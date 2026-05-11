use crate::error::{Result, VentoError};

// Protocol framing constants
pub const CMD_PAGE: u8 = 0xFF;
pub const CMD_FUNC: u8 = 0xFC;
pub const CMD_SIZE: u8 = 0xFE;
pub const CMD_NOT_SUP: u8 = 0xFD;
pub const PACKET_START: [u8; 2] = [0xFD, 0xFD];
pub const PROTOCOL_TYPE: u8 = 0x02;
pub const DEFAULT_DEVICE_ID: &[u8; 16] = b"DEFAULT_DEVICEID";
pub const DEFAULT_PORT: u16 = 4000;
pub const MAX_PACKET_SIZE: usize = 256;

// Function capability flags (bitmask)
pub const FUNC_READ: u8 = 0b0001;
pub const FUNC_WRITE: u8 = 0b0010;
pub const FUNC_INC: u8 = 0b0100;
pub const FUNC_DEC: u8 = 0b1000;

pub const FUNC_R: u8 = FUNC_READ;
pub const FUNC_W: u8 = FUNC_WRITE;
pub const FUNC_RW: u8 = FUNC_READ | FUNC_WRITE;
pub const FUNC_RWID: u8 = FUNC_READ | FUNC_WRITE | FUNC_INC | FUNC_DEC;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum Func {
    Read = 0x01,
    Write = 0x02,
    WriteResp = 0x03,
    Increment = 0x04,
    Decrement = 0x05,
    Response = 0x06,
}

impl TryFrom<u8> for Func {
    type Error = ();
    fn try_from(v: u8) -> std::result::Result<Self, ()> {
        match v {
            0x01 => Ok(Func::Read),
            0x02 => Ok(Func::Write),
            0x03 => Ok(Func::WriteResp),
            0x04 => Ok(Func::Increment),
            0x05 => Ok(Func::Decrement),
            0x06 => Ok(Func::Response),
            _ => Err(()),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u16)]
pub enum Param {
    Power = 0x0001,
    Speed = 0x0002,
    BoostStatus = 0x0006,
    TimerMode = 0x0007,
    TimerCountdown = 0x000B,
    HumiditySensor = 0x000F,
    RelaySensor = 0x0014,
    VoltageSensor = 0x0016,
    HumidityThreshold = 0x0019,
    BatteryVoltage = 0x0024,
    CurrentHumidity = 0x0025,
    VoltageSensorVal = 0x002D,
    RelayState = 0x0032,
    ManualSpeed = 0x0044,
    Fan1Speed = 0x004A,
    Fan2Speed = 0x004B,
    FilterCountdown = 0x0064,
    FilterReset = 0x0065,
    BoostDelay = 0x0066,
    RtcTime = 0x006F,
    RtcCalendar = 0x0070,
    WeeklyScheduleEn = 0x0072,
    ScheduleSetup = 0x0077,
    DeviceSearch = 0x007C,
    DevicePassword = 0x007D,
    MachineHours = 0x007E,
    ResetAlarms = 0x0080,
    AlarmStatus = 0x0083,
    CloudPermission = 0x0085,
    FirmwareVersion = 0x0086,
    FactoryReset = 0x0087,
    FilterIndicator = 0x0088,
    WifiMode = 0x0094,
    WifiSsid = 0x0095,
    WifiPassword = 0x0096,
    WifiEncryption = 0x0099,
    WifiChannel = 0x009A,
    WifiDhcp = 0x009B,
    WifiIp = 0x009C,
    WifiSubnet = 0x009D,
    WifiGateway = 0x009E,
    WifiApply = 0x00A0,
    WifiDiscard = 0x00A2,
    WifiCurrentIp = 0x00A3,
    OperationMode = 0x00B7,
    VoltageThreshold = 0x00B8,
    UnitType = 0x00B9,
    HumidityStatus = 0x0304,
    VoltageStatus = 0x0305,
    NightTimer = 0x0302,
    PartyTimer = 0x0303,
}

impl Param {
    pub fn from_u16(v: u16) -> Option<Self> {
        match v {
            0x0001 => Some(Param::Power),
            0x0002 => Some(Param::Speed),
            0x0006 => Some(Param::BoostStatus),
            0x0007 => Some(Param::TimerMode),
            0x000B => Some(Param::TimerCountdown),
            0x000F => Some(Param::HumiditySensor),
            0x0014 => Some(Param::RelaySensor),
            0x0016 => Some(Param::VoltageSensor),
            0x0019 => Some(Param::HumidityThreshold),
            0x0024 => Some(Param::BatteryVoltage),
            0x0025 => Some(Param::CurrentHumidity),
            0x002D => Some(Param::VoltageSensorVal),
            0x0032 => Some(Param::RelayState),
            0x0044 => Some(Param::ManualSpeed),
            0x004A => Some(Param::Fan1Speed),
            0x004B => Some(Param::Fan2Speed),
            0x0064 => Some(Param::FilterCountdown),
            0x0065 => Some(Param::FilterReset),
            0x0066 => Some(Param::BoostDelay),
            0x006F => Some(Param::RtcTime),
            0x0070 => Some(Param::RtcCalendar),
            0x0072 => Some(Param::WeeklyScheduleEn),
            0x0077 => Some(Param::ScheduleSetup),
            0x007C => Some(Param::DeviceSearch),
            0x007D => Some(Param::DevicePassword),
            0x007E => Some(Param::MachineHours),
            0x0080 => Some(Param::ResetAlarms),
            0x0083 => Some(Param::AlarmStatus),
            0x0085 => Some(Param::CloudPermission),
            0x0086 => Some(Param::FirmwareVersion),
            0x0087 => Some(Param::FactoryReset),
            0x0088 => Some(Param::FilterIndicator),
            0x0094 => Some(Param::WifiMode),
            0x0095 => Some(Param::WifiSsid),
            0x0096 => Some(Param::WifiPassword),
            0x0099 => Some(Param::WifiEncryption),
            0x009A => Some(Param::WifiChannel),
            0x009B => Some(Param::WifiDhcp),
            0x009C => Some(Param::WifiIp),
            0x009D => Some(Param::WifiSubnet),
            0x009E => Some(Param::WifiGateway),
            0x00A0 => Some(Param::WifiApply),
            0x00A2 => Some(Param::WifiDiscard),
            0x00A3 => Some(Param::WifiCurrentIp),
            0x00B7 => Some(Param::OperationMode),
            0x00B8 => Some(Param::VoltageThreshold),
            0x00B9 => Some(Param::UnitType),
            0x0302 => Some(Param::NightTimer),
            0x0303 => Some(Param::PartyTimer),
            0x0304 => Some(Param::HumidityStatus),
            0x0305 => Some(Param::VoltageStatus),
            _ => None,
        }
    }

    pub fn as_u16(self) -> u16 {
        self as u16
    }

    /// High byte (page) of the parameter address.
    pub fn page(self) -> u8 {
        ((self as u16) >> 8) as u8
    }

    /// Low byte (address within page) of the parameter address.
    pub fn addr(self) -> u8 {
        (self as u16 & 0xFF) as u8
    }

    pub fn meta(self) -> ParamMeta {
        match self {
            Param::Power            => ParamMeta { func: FUNC_RW,   size: Some(1), not_a30: false },
            Param::Speed            => ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: false },
            Param::BoostStatus      => ParamMeta { func: FUNC_R,    size: Some(1), not_a30: false },
            Param::TimerMode        => ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: false },
            Param::TimerCountdown   => ParamMeta { func: FUNC_R,    size: Some(3), not_a30: false },
            Param::HumiditySensor   => ParamMeta { func: FUNC_RW,   size: Some(1), not_a30: false },
            Param::RelaySensor      => ParamMeta { func: FUNC_RW,   size: Some(1), not_a30: false },
            Param::VoltageSensor    => ParamMeta { func: FUNC_RW,   size: Some(1), not_a30: true  },
            Param::HumidityThreshold=> ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: false },
            Param::VoltageThreshold => ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: true  },
            Param::BatteryVoltage   => ParamMeta { func: FUNC_R,    size: Some(2), not_a30: false },
            Param::CurrentHumidity  => ParamMeta { func: FUNC_R,    size: Some(1), not_a30: false },
            Param::VoltageSensorVal => ParamMeta { func: FUNC_R,    size: Some(1), not_a30: true  },
            Param::RelayState       => ParamMeta { func: FUNC_R,    size: Some(1), not_a30: false },
            Param::HumidityStatus   => ParamMeta { func: FUNC_R,    size: Some(1), not_a30: false },
            Param::VoltageStatus    => ParamMeta { func: FUNC_R,    size: Some(1), not_a30: true  },
            Param::ManualSpeed      => ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: false },
            Param::Fan1Speed        => ParamMeta { func: FUNC_R,    size: Some(2), not_a30: false },
            Param::Fan2Speed        => ParamMeta { func: FUNC_R,    size: Some(2), not_a30: false },
            Param::FilterCountdown  => ParamMeta { func: FUNC_R,    size: Some(3), not_a30: false },
            Param::FilterReset      => ParamMeta { func: FUNC_W,    size: Some(1), not_a30: false },
            Param::FilterIndicator  => ParamMeta { func: FUNC_R,    size: Some(1), not_a30: false },
            Param::BoostDelay       => ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: false },
            Param::RtcTime          => ParamMeta { func: FUNC_RW,   size: Some(3), not_a30: false },
            Param::RtcCalendar      => ParamMeta { func: FUNC_RW,   size: Some(4), not_a30: false },
            Param::WeeklyScheduleEn => ParamMeta { func: FUNC_RW,   size: Some(1), not_a30: false },
            Param::ScheduleSetup    => ParamMeta { func: FUNC_RW,   size: Some(6), not_a30: false },
            Param::DeviceSearch     => ParamMeta { func: FUNC_R,    size: Some(16),not_a30: false },
            Param::DevicePassword   => ParamMeta { func: FUNC_RW,   size: None,    not_a30: false },
            Param::MachineHours     => ParamMeta { func: FUNC_R,    size: Some(4), not_a30: false },
            Param::ResetAlarms      => ParamMeta { func: FUNC_W,    size: Some(1), not_a30: false },
            Param::AlarmStatus      => ParamMeta { func: FUNC_R,    size: Some(1), not_a30: false },
            Param::CloudPermission  => ParamMeta { func: FUNC_RW,   size: Some(1), not_a30: false },
            Param::FirmwareVersion  => ParamMeta { func: FUNC_R,    size: Some(6), not_a30: false },
            Param::FactoryReset     => ParamMeta { func: FUNC_W,    size: Some(1), not_a30: false },
            Param::WifiMode         => ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: false },
            Param::WifiSsid         => ParamMeta { func: FUNC_RW,   size: None,    not_a30: false },
            Param::WifiPassword     => ParamMeta { func: FUNC_RW,   size: None,    not_a30: false },
            Param::WifiEncryption   => ParamMeta { func: FUNC_RW,   size: Some(1), not_a30: false },
            Param::WifiChannel      => ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: false },
            Param::WifiDhcp         => ParamMeta { func: FUNC_RW,   size: Some(1), not_a30: false },
            Param::WifiIp           => ParamMeta { func: FUNC_RW,   size: Some(4), not_a30: false },
            Param::WifiSubnet       => ParamMeta { func: FUNC_RW,   size: Some(4), not_a30: false },
            Param::WifiGateway      => ParamMeta { func: FUNC_RW,   size: Some(4), not_a30: false },
            Param::WifiApply        => ParamMeta { func: FUNC_W,    size: Some(1), not_a30: false },
            Param::WifiDiscard      => ParamMeta { func: FUNC_W,    size: Some(1), not_a30: false },
            Param::WifiCurrentIp    => ParamMeta { func: FUNC_R,    size: Some(4), not_a30: false },
            Param::OperationMode    => ParamMeta { func: FUNC_RWID, size: Some(1), not_a30: false },
            Param::UnitType         => ParamMeta { func: FUNC_R,    size: Some(2), not_a30: false },
            Param::NightTimer       => ParamMeta { func: FUNC_RW,   size: Some(2), not_a30: false },
            Param::PartyTimer       => ParamMeta { func: FUNC_RW,   size: Some(2), not_a30: false },
        }
    }
}

pub struct ParamMeta {
    pub func: u8,
    pub size: Option<u8>,
    pub not_a30: bool,
}

impl ParamMeta {
    pub fn is_readable(&self) -> bool  { self.func & FUNC_READ  != 0 }
    pub fn is_writable(&self) -> bool  { self.func & FUNC_WRITE != 0 }
    pub fn is_incrementable(&self) -> bool { self.func & FUNC_INC != 0 }
}

/// A (param, bytes) pair ready to be encoded into a write packet.
pub struct WriteParam(pub Param, pub Vec<u8>);

impl WriteParam {
    /// Encode an integer value for params with a fixed known size.
    pub fn from_int(param: Param, value: u64) -> Result<Self> {
        let size = param.meta().size.ok_or_else(|| {
            VentoError::Protocol(format!("{param:?} requires bytes value, not integer"))
        })? as usize;
        let mut bytes = vec![0u8; size];
        for (i, b) in bytes.iter_mut().enumerate() {
            *b = ((value >> (i * 8)) & 0xFF) as u8;
        }
        Ok(WriteParam(param, bytes))
    }

    /// Use pre-encoded bytes directly (variable-length params or multi-field values).
    pub fn from_bytes(param: Param, bytes: impl Into<Vec<u8>>) -> Self {
        WriteParam(param, bytes.into())
    }
}
