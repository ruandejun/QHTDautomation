use std::net::Ipv4Addr;
use std::str::FromStr;

pub struct NetworkAuditor;

#[derive(Debug, PartialEq, Clone)]
pub enum DnsMode {
    RedirHost,
    FakeIp,
}

impl NetworkAuditor {
    /// Kiểm tra xem IP có bị xung đột hoặc rơi vào blackhole hay không
    pub fn validate_ip_inclusion(ip_str: &str, exclude_list: &[String]) -> Result<bool, String> {
        let ip = Ipv4Addr::from_str(ip_str).map_err(|e| format!("Invalid IP: {}", e))?;
        for exc in exclude_list {
            if exc.contains('/') {
                let parts: Vec<&str> = exc.split('/').collect();
                if let (Ok(net_ip), Ok(prefix)) = (Ipv4Addr::from_str(parts[0]), parts[1].parse::<u32>()) {
                    if prefix <= 32 {
                        let mask = if prefix == 0 { 0 } else { !0u32 << (32 - prefix) };
                        let ip_u32 = u32::from(ip);
                        let net_u32 = u32::from(net_ip);
                        if (ip_u32 & mask) == (net_u32 & mask) {
                            return Ok(false); // Bị loại trừ (bị exclude)
                        }
                    }
                }
            } else if let Ok(exc_ip) = Ipv4Addr::from_str(exc) {
                if ip == exc_ip {
                    return Ok(false);
                }
            }
        }
        Ok(true) // Hợp lệ, đi qua TUN
    }

    /// Đảm bảo DNS Hijack bao quát cả UDP và TCP cổng 53
    pub fn get_recommended_dns_hijack() -> Vec<String> {
        vec!["any:53".to_string(), "tcp://any:53".to_string()]
    }

    /// Đảm bảo DNS Mode phù hợp cho môi trường Phone Farm Hotspot
    pub fn get_recommended_dns_mode() -> DnsMode {
        DnsMode::RedirHost
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gateway_not_excluded() {
        let exclude_list = vec![
            "127.0.0.0/8".to_string(),
            "192.168.1.0/24".to_string(), // WAN
            "172.19.0.0/30".to_string(),
        ];
        // Gateway hotspot 192.168.137.1 KHÔNG được bị exclude
        let is_included = NetworkAuditor::validate_ip_inclusion("192.168.137.1", &exclude_list).unwrap();
        assert!(is_included, "Gateway 192.168.137.1 must be routed to capture DNS port 53");

        // WAN subnet bị exclude đúng chuẩn
        let wan_included = NetworkAuditor::validate_ip_inclusion("192.168.1.100", &exclude_list).unwrap();
        assert!(!wan_included, "WAN IP must be excluded to prevent routing loop");
    }

    #[test]
    fn test_dns_hijack_rules() {
        let hijack = NetworkAuditor::get_recommended_dns_hijack();
        assert!(hijack.contains(&"any:53".to_string()));
        assert!(hijack.contains(&"tcp://any:53".to_string()));
    }
}
