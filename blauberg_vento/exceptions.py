class VentoError(Exception): pass
class VentoConnectionError(VentoError): pass
class VentoChecksumError(VentoError): pass
class VentoProtocolError(VentoError): pass
class VentoAuthError(VentoError): pass
class VentoValueError(VentoError): pass
class VentoDiscoveryError(VentoError): pass
class VentoUnsupportedParamError(VentoError):
    def __init__(self, params):
        self.params = params
        super().__init__(f"Unsupported parameters: {[hex(p) for p in params]}")
