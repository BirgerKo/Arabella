use std::net::UdpSocket;
use std::time::Duration;

use crate::error::{Result, VentoError};

const UDP_BUFFER_SIZE: usize = 1024;

pub struct VentoTransport {
    pub timeout: Duration,
}

impl VentoTransport {
    pub fn new(timeout_secs: f64) -> Self {
        VentoTransport {
            timeout: Duration::from_secs_f64(timeout_secs),
        }
    }

    /// Send a packet and receive a single response.
    pub fn send_recv(&self, host: &str, packet: &[u8], port: u16) -> Result<Vec<u8>> {
        let socket = UdpSocket::bind("0.0.0.0:0")
            .map_err(|e| VentoError::Connection(format!("bind error: {e}")))?;
        socket
            .set_read_timeout(Some(self.timeout))
            .map_err(|e| VentoError::Connection(format!("set_timeout error: {e}")))?;
        socket
            .send_to(packet, (host, port))
            .map_err(|e| VentoError::Connection(format!("send_to {host}:{port}: {e}")))?;

        let mut buf = vec![0u8; UDP_BUFFER_SIZE];
        match socket.recv_from(&mut buf) {
            Ok((n, _)) => Ok(buf[..n].to_vec()),
            Err(e) if is_timeout(&e) => {
                Err(VentoError::Connection(format!("Timeout from {host}:{port}")))
            }
            Err(e) => Err(VentoError::Connection(format!("Socket error {host}:{port}: {e}"))),
        }
    }

    /// Send a packet with no response expected (WRITE without response).
    pub fn send_only(&self, host: &str, packet: &[u8], port: u16) -> Result<()> {
        let socket = UdpSocket::bind("0.0.0.0:0")
            .map_err(|e| VentoError::Connection(format!("bind error: {e}")))?;
        socket
            .send_to(packet, (host, port))
            .map_err(|e| VentoError::Connection(format!("send_to {host}:{port}: {e}")))?;
        Ok(())
    }

    /// Broadcast a discovery packet and collect all responses within the timeout.
    pub fn discover(
        &self,
        packet: &[u8],
        broadcast: &str,
        port: u16,
        max_devices: usize,
    ) -> Result<Vec<(String, Vec<u8>)>> {
        let socket = UdpSocket::bind("0.0.0.0:0")
            .map_err(|e| VentoError::Discovery(format!("bind error: {e}")))?;
        socket
            .set_broadcast(true)
            .map_err(|e| VentoError::Discovery(format!("set_broadcast: {e}")))?;
        socket
            .set_read_timeout(Some(self.timeout))
            .map_err(|e| VentoError::Discovery(format!("set_timeout: {e}")))?;
        socket
            .send_to(packet, (broadcast, port))
            .map_err(|e| VentoError::Discovery(format!("send discovery: {e}")))?;

        let mut results = Vec::new();
        let mut buf = vec![0u8; UDP_BUFFER_SIZE];
        while results.len() < max_devices {
            match socket.recv_from(&mut buf) {
                Ok((n, addr)) => results.push((addr.ip().to_string(), buf[..n].to_vec())),
                Err(e) if is_timeout(&e) => break,
                Err(e) => return Err(VentoError::Discovery(format!("recv error: {e}"))),
            }
        }
        Ok(results)
    }
}

fn is_timeout(e: &std::io::Error) -> bool {
    matches!(
        e.kind(),
        std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut
    )
}

impl Default for VentoTransport {
    fn default() -> Self {
        VentoTransport::new(3.0)
    }
}
