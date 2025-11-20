"""IPMI command helpers for interacting with BMCs."""
from __future__ import annotations

import asyncio

from app.core.security import SecretManager
from app.models.server import ServerTarget


class IPMICommandError(RuntimeError):
    """Raised when ipmitool encounters an error."""


class IPMIClient:
    """Execute ipmitool commands for a specific server target."""

    def __init__(self, server: ServerTarget, secret_manager: SecretManager) -> None:
        self.server = server
        self.secret_manager = secret_manager

    @property
    def _credentials(self) -> tuple[str, str]:
        username = self.secret_manager.decrypt(self.server.username_encrypted)
        password = self.secret_manager.decrypt(self.server.password_encrypted)
        return username, password

    async def _run(self, raw_args: list[str]) -> str:
        username, password = self._credentials
        base_cmd = [
            "ipmitool",
            "-I",
            "lanplus",
            "-H",
            self.server.bmc_host,
            "-U",
            username,
            "-P",
            password,
        ]
        cmd = base_cmd + raw_args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise IPMICommandError(stderr.decode().strip())
        return stdout.decode().strip()

    async def query_fans(self) -> str:
        """Return textual fan status for the server."""

        return await self._run(["sdr", "type", "Fan"])

    async def query_temperatures(self) -> str:
        """Return textual temperature status for the server."""

        return await self._run(["sdr", "type", "Temperature"])

    async def query_memory_status(self) -> str:
        """Return memory status and errors from IPMI."""
        try:
            return await self._run(["sdr", "type", "Memory"])
        except IPMICommandError:
            # Some servers may not have memory SDR entries, try SEL instead
            return ""

    async def query_power_supply_status(self) -> str:
        """Return power supply status from IPMI."""
        try:
            return await self._run(["sdr", "type", "Power Supply"])
        except IPMICommandError:
            return ""

    async def query_chassis_intrusion(self) -> str:
        """Return chassis intrusion status from IPMI."""
        try:
            return await self._run(["sdr", "type", "Physical Security"])
        except IPMICommandError:
            # Try alternative command
            try:
                return await self._run(["sdr", "get", "Chassis Intrusion"])
            except IPMICommandError:
                return ""

    async def query_system_events(self, limit: int = 10) -> str:
        """Return recent system event log entries."""
        try:
            return await self._run(["sel", "elist", "-c", str(limit)])
        except IPMICommandError:
            return ""

    async def query_voltage_status(self) -> str:
        """Return voltage sensor status from IPMI."""
        try:
            return await self._run(["sdr", "type", "Voltage"])
        except IPMICommandError:
            return ""

    async def raw_command(self, payload: str) -> str:
        """Execute a raw IPMI command from a hex string (e.g. "0x30 0x70 ...")."""

        args = ["raw"] + payload.split()
        return await self._run(args)

    async def apply_supermicro_optimal_floor(self) -> str:
        """Apply the default raw command for Supermicro rpm reduction."""

        return await self.raw_command("0x30 0x70 0x66 0x01 0x00 0x00 0x18")

    async def set_fan_speed(self, target_rpm: int, fan_identifier: str | None = None) -> str:
        """Adjust fan speed using vendor-specific logic.

        For now this simply logs the intention and returns immediately. Future
        iterations will map to precise vendor commands.
        """

        command = _build_fan_command(self.server.vendor, target_rpm, fan_identifier)
        return await self.raw_command(command)


def _build_fan_command(vendor: str, target_rpm: int, fan_identifier: str | None) -> str:
    """Build vendor-specific IPMI raw command to set fan speed.
    
    Args:
        vendor: Server vendor (supermicro, dell, hp)
        target_rpm: Target RPM (0 = full speed, or specific RPM value)
        fan_identifier: Optional fan identifier for per-fan control
    
    Returns:
        Raw IPMI command string (e.g., "0x30 0x70 0x66 0x01 0x00 0x00 0x18")
    """
    vendor = vendor.lower()
    if vendor == "supermicro":
        # Supermicro fan control command format:
        # 0x30 0x70 0x66 0x01 0x00 0x00 <speed_byte>
        # Where speed_byte is typically:
        # - 0x00-0x14 (0-20): Very low/quiet mode
        # - 0x18 (24): Optimal/balanced mode (default ~3500 RPM)
        # - 0x64 (100): Full speed
        
        if target_rpm == 0:
            # Full speed
            speed_byte = 0x64
        elif target_rpm <= 2000:
            # Low RPM mode (1800 RPM range) - use 0x18 which sets "optimal" that can go low
            # Note: The exact RPM may vary, but this should reduce fan speed significantly
            speed_byte = 0x18
        elif target_rpm <= 3500:
            # Medium RPM mode - balanced
            speed_byte = 0x30
        else:
            # Higher RPM - closer to full speed
            # Map RPM to approximate percentage (assuming max ~5000 RPM)
            percentage = min(100, int((target_rpm / 5000) * 100))
            speed_byte = min(0x64, int((percentage / 100) * 0x64))
        
        # Convert speed_byte to hex string
        speed_hex = hex(speed_byte)
        
        # Zone 0x01 = apply to all fans, 0x00 = apply to specific zone
        zone = 0x01 if fan_identifier is None else 0x00
        
        return f"0x30 0x70 0x66 {hex(zone)} 0x00 0x00 {speed_hex}"
    
    if vendor == "dell":
        # TODO: implement Dell iDRAC raw command mapping.
        raise NotImplementedError("Dell fan control not yet implemented")
    if vendor == "hp":
        raise NotImplementedError("HP iLO fan control not yet implemented")
    raise ValueError(f"Unsupported vendor: {vendor}")
