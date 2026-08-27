use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InterfaceInfo {
    pub index: u32,
    pub alias: String,
    pub description: String,
    pub ip_addresses: Vec<String>,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouterConfig {
    pub lan_interface: String,
    pub wan_interface: String,
    pub router_ip: String,
    pub dhcp_start: String,
    pub dhcp_end: String,
    pub proxy_rules: Vec<ProxyRule>,
    pub dns_servers: Vec<String>,
    pub hotspot_24ghz_only: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProxyRule {
    pub name: String,
    pub target_ips: Vec<String>,
    pub proxy_url: String,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceLease {
    pub ip: String,
    pub mac: String,
    pub hostname: String,
    pub lease_time: String,
    pub assigned_proxy: Option<String>,
}

pub struct C69RouterManager {
    pub work_dir: PathBuf,
    pub bin_dir: PathBuf,
}

impl C69RouterManager {
    pub fn new<P: AsRef<Path>>(work_dir: P) -> Self {
        let work_path = work_dir.as_ref().to_path_buf();
        let bin_path = work_path.join("bin");
        Self {
            work_dir: work_path,
            bin_dir: bin_path,
        }
    }

    /// Lấy danh sách card mạng đang hoạt động
    pub fn list_network_interfaces() -> Vec<InterfaceInfo> {
        let mut interfaces = Vec::new();

        #[cfg(target_os = "windows")]
        {
            let output = Command::new("powershell")
                .args(&[
                    "-NoProfile",
                    "-Command",
                    "Get-NetIPConfiguration | ForEach-Object { [PSCustomObject]@{ Index=$_.InterfaceIndex; Alias=$_.InterfaceAlias; Desc=$_.InterfaceDescription; IPv4=($_.IPv4Address.IPAddress -join ','); Status=$_.NetAdapter.Status } } | ConvertTo-Json"
                ])
                .output();

            if let Ok(out) = output {
                if let Ok(json_str) = String::from_utf8(out.stdout) {
                    if let Ok(val) = serde_json::from_str::<serde_json::Value>(&json_str) {
                        if let Some(arr) = val.as_array() {
                            for item in arr {
                                interfaces.push(InterfaceInfo {
                                    index: item.get("Index").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
                                    alias: item.get("Alias").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                                    description: item.get("Desc").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                                    ip_addresses: item.get("IPv4").and_then(|v| v.as_str()).unwrap_or("").split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect(),
                                    status: item.get("Status").and_then(|v| v.as_str()).unwrap_or("Up").to_string(),
                                });
                            }
                        }
                    }
                }
            }
        }

        #[cfg(not(target_os = "windows"))]
        {
            interfaces.push(InterfaceInfo {
                index: 1,
                alias: "eth0".to_string(),
                description: "Primary Ethernet Adapter".to_string(),
                ip_addresses: vec!["180.93.54.68".to_string()],
                status: "Up".to_string(),
            });
            interfaces.push(InterfaceInfo {
                index: 2,
                alias: "lan_phonefarm0".to_string(),
                description: "Virtual PhoneFarm Bridge".to_string(),
                ip_addresses: vec!["192.168.88.1".to_string()],
                status: "Up".to_string(),
            });
        }

        interfaces
    }

    /// Sinh cấu hình Mihomo/Clash Core (clash-config.yaml) chuẩn OpenClash tốc độ cao
    pub fn generate_clash_yaml_config(&self, config: &RouterConfig) -> Result<String, String> {
        let mut yaml = String::new();
        
        yaml.push_str("port: 7890\n");
        yaml.push_str("socks-port: 7891\n");
        yaml.push_str("mixed-port: 7892\n");
        yaml.push_str("allow-lan: true\n");
        yaml.push_str("mode: rule\n");
        yaml.push_str("log-level: warning\n");
        yaml.push_str("ipv6: false\n");
        yaml.push_str("external-controller: 127.0.0.1:9090\n\n");

        // TUN config (Mihomo / Clash Meta)
        yaml.push_str("tun:\n");
        yaml.push_str("  enable: true\n");
        yaml.push_str("  stack: mixed\n");
        yaml.push_str("  device: c69-wintun\n");
        yaml.push_str("  auto-route: true\n");
        yaml.push_str("  auto-detect-interface: true\n");
        yaml.push_str("  dns-hijack:\n");
        yaml.push_str("    - \"any:53\"\n");
        yaml.push_str("    - \"tcp://any:53\"\n\n");

        // DNS config
        yaml.push_str("dns:\n");
        yaml.push_str("  enable: true\n");
        yaml.push_str("  listen: 0.0.0.0:1053\n");
        yaml.push_str("  enhanced-mode: fake-ip\n");
        yaml.push_str("  fake-ip-range: 198.18.0.1/16\n");
        yaml.push_str("  nameserver:\n");
        for dns in &config.dns_servers {
            yaml.push_str(&format!("    - \"{}\"\n", dns));
        }
        yaml.push_str("\n");

        // Proxies
        yaml.push_str("proxies:\n");
        for (i, rule) in config.proxy_rules.iter().enumerate() {
            if !rule.enabled {
                continue;
            }
            let host = rule.proxy_url.split(':').next().unwrap_or("127.0.0.1");
            let port = rule.proxy_url.split(':').nth(1).unwrap_or("1080");
            yaml.push_str(&format!("  - name: \"proxy-{}\"\n", i));
            yaml.push_str("    type: socks5\n");
            yaml.push_str(&format!("    server: {}\n", host));
            yaml.push_str(&format!("    port: {}\n", port));
            yaml.push_str("    udp: true\n");
        }
        yaml.push_str("\n");

        // Rules
        yaml.push_str("rules:\n");
        yaml.push_str("  - DST-PORT,9000,DIRECT\n");
        yaml.push_str("  - DST-PORT,8000,DIRECT\n");
        for (i, rule) in config.proxy_rules.iter().enumerate() {
            if !rule.enabled {
                continue;
            }
            for ip in &rule.target_ips {
                yaml.push_str(&format!("  - SRC-IP-CIDR,{},\"proxy-{}\"\n", ip, i));
            }
        }
        yaml.push_str("  - MATCH,DIRECT\n");

        Ok(yaml)
    }

    /// Đọc danh sách MAC & IP Lease của các máy Android kết nối vào mạng
    pub fn get_active_leases(&self) -> Vec<DeviceLease> {
        let registry_path = self.work_dir.join("data").join("mac_registry.json");
        let mut leases = Vec::new();

        if registry_path.exists() {
            if let Ok(content) = fs::read_to_string(&registry_path) {
                if let Ok(map) = serde_json::from_str::<HashMap<String, serde_json::Value>>(&content) {
                    for (mac, val) in map {
                        leases.push(DeviceLease {
                            ip: val.get("ip").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                            mac: mac.clone(),
                            hostname: val.get("hostname").and_then(|v| v.as_str()).unwrap_or("Android-Device").to_string(),
                            lease_time: val.get("time").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                            assigned_proxy: val.get("proxy").and_then(|v| v.as_str()).map(|s| s.to_string()),
                        });
                    }
                }
            }
        }

        leases
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_list_interfaces() {
        let ifaces = C69RouterManager::list_network_interfaces();
        assert!(!ifaces.is_empty());
    }

    #[test]
    fn test_clash_yaml_config_generation() {
        let manager = C69RouterManager::new("/tmp/test_c69_router");
        let config = RouterConfig {
            lan_interface: "Ethernet 2".to_string(),
            wan_interface: "Ethernet".to_string(),
            router_ip: "192.168.88.1".to_string(),
            dhcp_start: "192.168.88.100".to_string(),
            dhcp_end: "192.168.88.250".to_string(),
            proxy_rules: vec![
                ProxyRule {
                    name: "Phone 1 Proxy".to_string(),
                    target_ips: vec!["192.168.88.101/32".to_string()],
                    proxy_url: "127.0.0.1:1080".to_string(),
                    enabled: true,
                }
            ],
            dns_servers: vec!["8.8.8.8".to_string()],
            hotspot_24ghz_only: true,
        };

        let yaml_str = manager.generate_clash_yaml_config(&config).unwrap();
        assert!(yaml_str.contains("device: c69-wintun"));
        assert!(yaml_str.contains("fake-ip-range: 198.18.0.1/16"));
        assert!(yaml_str.contains("proxy-0"));
        assert!(yaml_str.contains("SRC-IP-CIDR,192.168.88.101/32,\"proxy-0\""));
    }
}
