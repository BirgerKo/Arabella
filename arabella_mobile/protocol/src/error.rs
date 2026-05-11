use std::fmt;

#[derive(Debug)]
pub enum VentoError {
    Connection(String),
    Checksum(String),
    Protocol(String),
    Value(String),
    Discovery(String),
    UnsupportedParams(Vec<u16>),
    Io(std::io::Error),
}

impl fmt::Display for VentoError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            VentoError::Connection(s)        => write!(f, "Connection error: {s}"),
            VentoError::Checksum(s)          => write!(f, "Checksum error: {s}"),
            VentoError::Protocol(s)          => write!(f, "Protocol error: {s}"),
            VentoError::Value(s)             => write!(f, "Value error: {s}"),
            VentoError::Discovery(s)         => write!(f, "Discovery error: {s}"),
            VentoError::UnsupportedParams(p) => write!(f, "Unsupported parameters: {p:?}"),
            VentoError::Io(e)                => write!(f, "IO error: {e}"),
        }
    }
}

impl std::error::Error for VentoError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        if let VentoError::Io(e) = self {
            Some(e)
        } else {
            None
        }
    }
}

impl From<std::io::Error> for VentoError {
    fn from(e: std::io::Error) -> Self {
        VentoError::Io(e)
    }
}

pub type Result<T> = std::result::Result<T, VentoError>;
