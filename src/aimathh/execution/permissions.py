"""Capability-based permissions for every tool execution."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    INSTALL = "install"


class PermissionSet(BaseModel):
    allowed: set[Permission] = {Permission.READ, Permission.EXECUTE}

    def allows(self, perm: Permission) -> bool:
        return perm in self.allowed

    def require(self, perm: Permission) -> None:
        from aimathh.core.errors import PermissionDeniedError

        if perm not in self.allowed:
            raise PermissionDeniedError(
                f"Permission '{perm.value}' denied for this tool call",
                details={"allowed": sorted(p.value for p in self.allowed)},
            )


def default_permissions(*, network: bool = False, install: bool = False, write: bool = True) -> PermissionSet:
    allowed: set[Permission] = {Permission.READ, Permission.EXECUTE}
    if write:
        allowed.add(Permission.WRITE)
    if network:
        allowed.add(Permission.NETWORK)
    if install:
        allowed.add(Permission.INSTALL)
    return PermissionSet(allowed=allowed)
