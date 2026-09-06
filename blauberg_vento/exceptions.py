class VentoError(Exception):
    """Base exception for all Blauberg Vento client failures."""


class VentoConnectionError(VentoError):
    """Raised when a UDP socket operation cannot complete."""


class VentoTimeoutError(VentoConnectionError):
    """Raised when a request exceeds the configured timeout."""


class VentoChecksumError(VentoError):
    """Raised when a packet checksum does not match the payload."""


class VentoProtocolError(VentoError):
    """Raised when a packet structure or protocol field is invalid."""


class VentoInvalidResponseError(VentoProtocolError):
    """Raised when a packet does not match the expected device response format."""


class VentoAuthError(VentoError):
    """Raised when authentication or authorization to the device fails."""


class VentoValueError(VentoError):
    """Raised when an invalid parameter value is supplied."""


class VentoDiscoveryError(VentoError):
    """Raised when UDP discovery cannot complete."""


class VentoUnsupportedParamError(VentoError):
    def __init__(self, params: list[int]) -> None:
        self.params: list[int] = params
        super().__init__(f"Unsupported parameters: {[hex(p) for p in self.params]}")
