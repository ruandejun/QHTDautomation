// MunAntiBrowser - WebRTC IP Leak Protection (v3)
// Prevents real IP leakage through WebRTC STUN/TURN requests.
// Strategy: 
//   1. Remove all STUN servers from iceServers config
//   2. Filter ICE candidates (remove srflx with public IPs)
//   3. Sanitize SDP offer/answer to remove real IPs
//   4. Wrap addEventListener for icecandidate events

(function protectWebRTC() {
  'use strict';

  var _RTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
  if (!_RTCPeerConnection) return;

  // Regex to match public IPv4 and IPv6 addresses
  var PUBLIC_IP_RE = /([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})/g;
  var IPV6_RE = /([0-9a-f]{1,4}(:[0-9a-f]{1,4}){2,7})/gi;

  function isPrivateIP(ip) {
    if (!ip) return true;
    if (ip.indexOf('10.') === 0) return true;
    if (ip.indexOf('192.168.') === 0) return true;
    if (ip.indexOf('127.') === 0) return true;
    if (ip === '0.0.0.0') return true;
    if (ip.indexOf('172.') === 0) {
      var second = parseInt(ip.split('.')[1]);
      if (second >= 16 && second <= 31) return true;
    }
    // mDNS addresses (*.local) are safe
    if (ip.indexOf('.local') !== -1) return true;
    return false;
  }

  function isPrivateIPv6(ip) {
    if (!ip) return true;
    if (ip === '::1') return true;
    if (ip.indexOf('fe80:') === 0) return true;  // link-local
    if (ip.indexOf('fc') === 0 || ip.indexOf('fd') === 0) return true;  // unique local
    return false;
  }

  // Sanitize SDP: remove lines containing public IPs
  function sanitizeSDP(sdp) {
    if (!sdp) return sdp;
    var lines = sdp.split('\r\n');
    var filtered = lines.filter(function(line) {
      // Remove candidate lines with srflx (server reflexive = real public IP)
      if (line.indexOf('a=candidate:') === 0 && line.indexOf('srflx') !== -1) {
        return false;
      }
      // Remove candidate lines with public IPs (non-private)
      if (line.indexOf('a=candidate:') === 0) {
        var ipMatch = line.match(PUBLIC_IP_RE);
        if (ipMatch) {
          for (var i = 0; i < ipMatch.length; i++) {
            if (!isPrivateIP(ipMatch[i])) return false;
          }
        }
        // Check IPv6
        var ip6Match = line.match(IPV6_RE);
        if (ip6Match) {
          for (var j = 0; j < ip6Match.length; j++) {
            if (!isPrivateIPv6(ip6Match[j])) return false;
          }
        }
      }
      // Replace public IP in c= (connection) lines with 0.0.0.0
      if (line.indexOf('c=IN IP4') === 0) {
        return true; // Keep but we'll replace below
      }
      return true;
    });

    // Replace public IPs in c= lines
    var result = filtered.join('\r\n');
    result = result.replace(/c=IN IP4 ([0-9.]+)/g, function(match, ip) {
      if (!isPrivateIP(ip)) return 'c=IN IP4 0.0.0.0';
      return match;
    });
    result = result.replace(/c=IN IP6 ([0-9a-f:]+)/gi, function(match, ip) {
      if (!isPrivateIPv6(ip)) return 'c=IN IP6 ::';
      return match;
    });

    return result;
  }

  // Check if ICE candidate leaks real IP
  function isLeakyCandidate(candidate) {
    if (!candidate || !candidate.candidate) return false;
    var c = candidate.candidate;
    // Block srflx entirely
    if (c.indexOf('srflx') !== -1) return true;
    // Check for public IPv4
    var ipMatch = c.match(PUBLIC_IP_RE);
    if (ipMatch) {
      for (var i = 0; i < ipMatch.length; i++) {
        if (!isPrivateIP(ipMatch[i])) return true;
      }
    }
    // Check IPv6
    var ip6Match = c.match(IPV6_RE);
    if (ip6Match) {
      for (var j = 0; j < ip6Match.length; j++) {
        if (!isPrivateIPv6(ip6Match[j])) return true;
      }
    }
    return false;
  }

  // Patched RTCPeerConnection
  var PatchedRTC = function(config, constraints) {
    // Strip STUN servers
    if (config && config.iceServers) {
      config.iceServers = config.iceServers.filter(function(server) {
        var urls = server.urls || server.url || [];
        if (typeof urls === 'string') urls = [urls];
        for (var i = 0; i < urls.length; i++) {
          if (typeof urls[i] === 'string' && urls[i].toLowerCase().indexOf('stun:') === 0) {
            return false;
          }
        }
        return true;
      });
    }

    var pc = constraints ? new _RTCPeerConnection(config, constraints)
                        : new _RTCPeerConnection(config);

    // --- Wrap setLocalDescription to sanitize SDP ---
    var _origSetLocal = pc.setLocalDescription.bind(pc);
    pc.setLocalDescription = function(desc) {
      if (desc && desc.sdp) {
        desc = new RTCSessionDescription({
          type: desc.type,
          sdp: sanitizeSDP(desc.sdp)
        });
      }
      return _origSetLocal(desc);
    };

    // --- Wrap setRemoteDescription to sanitize SDP ---
    var _origSetRemote = pc.setRemoteDescription.bind(pc);
    pc.setRemoteDescription = function(desc) {
      if (desc && desc.sdp) {
        desc = new RTCSessionDescription({
          type: desc.type,
          sdp: sanitizeSDP(desc.sdp)
        });
      }
      return _origSetRemote(desc);
    };

    // --- Wrap createOffer to sanitize returned SDP ---
    var _origCreateOffer = pc.createOffer.bind(pc);
    pc.createOffer = function(options) {
      return _origCreateOffer(options).then(function(offer) {
        if (offer && offer.sdp) {
          offer = new RTCSessionDescription({
            type: offer.type,
            sdp: sanitizeSDP(offer.sdp)
          });
        }
        return offer;
      });
    };

    // --- Wrap createAnswer to sanitize returned SDP ---
    var _origCreateAnswer = pc.createAnswer.bind(pc);
    pc.createAnswer = function(options) {
      return _origCreateAnswer(options).then(function(answer) {
        if (answer && answer.sdp) {
          answer = new RTCSessionDescription({
            type: answer.type,
            sdp: sanitizeSDP(answer.sdp)
          });
        }
        return answer;
      });
    };

    // --- Wrap localDescription getter to sanitize ---
    var _descProp = Object.getOwnPropertyDescriptor(pc.__proto__, 'localDescription') ||
                    Object.getOwnPropertyDescriptor(_RTCPeerConnection.prototype, 'localDescription');
    if (_descProp && _descProp.get) {
      var _origLocalDescGet = _descProp.get.bind(pc);
      Object.defineProperty(pc, 'localDescription', {
        get: function() {
          var desc = _origLocalDescGet();
          if (desc && desc.sdp) {
            return new RTCSessionDescription({
              type: desc.type,
              sdp: sanitizeSDP(desc.sdp)
            });
          }
          return desc;
        },
        configurable: true, enumerable: true
      });
    }

    // --- Wrap onicecandidate ---
    var _userHandler = null;
    Object.defineProperty(pc, 'onicecandidate', {
      get: function() { return _userHandler; },
      set: function(handler) {
        _userHandler = function(event) {
          if (event && event.candidate && isLeakyCandidate(event.candidate)) {
            return; // Block
          }
          if (handler) handler(event);
        };
      },
      configurable: true, enumerable: true
    });

    // --- Wrap addEventListener('icecandidate') ---
    var _origAddEvt = pc.addEventListener.bind(pc);
    pc.addEventListener = function(type, listener, opts) {
      if (type === 'icecandidate') {
        var wrapped = function(event) {
          if (event && event.candidate && isLeakyCandidate(event.candidate)) {
            return;
          }
          listener.call(pc, event);
        };
        return _origAddEvt(type, wrapped, opts);
      }
      return _origAddEvt(type, listener, opts);
    };

    return pc;
  };

  // Preserve prototype chain
  PatchedRTC.prototype = _RTCPeerConnection.prototype;
  if (_RTCPeerConnection.generateCertificate) {
    PatchedRTC.generateCertificate = _RTCPeerConnection.generateCertificate;
  }

  // Native toString
  try {
    Object.defineProperty(PatchedRTC, 'name', { value: 'RTCPeerConnection', configurable: true });
    Object.defineProperty(PatchedRTC, 'toString', {
      value: function() { return 'function RTCPeerConnection() { [native code] }'; },
      configurable: true, writable: true
    });
  } catch (e) {}

  // Replace globals
  window.RTCPeerConnection = PatchedRTC;
  if (window.webkitRTCPeerConnection) {
    window.webkitRTCPeerConnection = PatchedRTC;
  }
})();
