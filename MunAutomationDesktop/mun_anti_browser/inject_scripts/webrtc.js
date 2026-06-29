// MunAntiBrowser - WebRTC IP Leak Protection (v3)
// Prevents real IP leakage through WebRTC STUN/TURN requests.

(function protectWebRTC() {
  'use strict';

  var _RTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
  if (!_RTCPeerConnection) return;

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
    if (ip.indexOf('.local') !== -1) return true;
    return false;
  }

  function isPrivateIPv6(ip) {
    if (!ip) return true;
    if (ip === '::1') return true;
    if (ip.indexOf('fe80:') === 0) return true;
    if (ip.indexOf('fc') === 0 || ip.indexOf('fd') === 0) return true;
    return false;
  }

  function sanitizeSDP(sdp) {
    if (!sdp) return sdp;
    var lines = sdp.split('\r\n');
    var filtered = lines.filter(function(line) {
      if (line.indexOf('a=candidate:') === 0 && line.indexOf('srflx') !== -1) {
        return false;
      }
      if (line.indexOf('a=candidate:') === 0) {
        var ipMatch = line.match(PUBLIC_IP_RE);
        if (ipMatch) {
          for (var i = 0; i < ipMatch.length; i++) {
            if (!isPrivateIP(ipMatch[i])) return false;
          }
        }
        var ip6Match = line.match(IPV6_RE);
        if (ip6Match) {
          for (var j = 0; j < ip6Match.length; j++) {
            if (!isPrivateIPv6(ip6Match[j])) return false;
          }
        }
      }
      return true;
    });

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

  function isLeakyCandidate(candidate) {
    if (!candidate || !candidate.candidate) return false;
    var c = candidate.candidate;
    if (c.indexOf('srflx') !== -1) return true;
    var ipMatch = c.match(PUBLIC_IP_RE);
    if (ipMatch) {
      for (var i = 0; i < ipMatch.length; i++) {
        if (!isPrivateIP(ipMatch[i])) return true;
      }
    }
    var ip6Match = c.match(IPV6_RE);
    if (ip6Match) {
      for (var j = 0; j < ip6Match.length; j++) {
        if (!isPrivateIPv6(ip6Match[j])) return true;
      }
    }
    return false;
  }

  var PatchedRTC = function RTCPeerConnection(config, constraints) {
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
    return constraints ? new _RTCPeerConnection(config, constraints)
                        : new _RTCPeerConnection(config);
  };

  PatchedRTC.prototype = _RTCPeerConnection.prototype;
  if (_RTCPeerConnection.generateCertificate) {
    PatchedRTC.generateCertificate = _RTCPeerConnection.generateCertificate;
  }

  var proto = _RTCPeerConnection.prototype;

  if (proto.setLocalDescription) {
    var _origSetLocal = proto.setLocalDescription;
    var setLocalDescription = function setLocalDescription(desc) {
      if (desc && desc.sdp) {
        desc = new RTCSessionDescription({
          type: desc.type,
          sdp: sanitizeSDP(desc.sdp)
        });
      }
      return _origSetLocal.apply(this, arguments);
    };
    if (window._safelyOverrideValue) {
      window._safelyOverrideValue(proto, 'setLocalDescription', setLocalDescription);
    } else {
      proto.setLocalDescription = setLocalDescription;
    }
  }

  if (proto.setRemoteDescription) {
    var _origSetRemote = proto.setRemoteDescription;
    var setRemoteDescription = function setRemoteDescription(desc) {
      if (desc && desc.sdp) {
        desc = new RTCSessionDescription({
          type: desc.type,
          sdp: sanitizeSDP(desc.sdp)
        });
      }
      return _origSetRemote.apply(this, arguments);
    };
    if (window._safelyOverrideValue) {
      window._safelyOverrideValue(proto, 'setRemoteDescription', setRemoteDescription);
    } else {
      proto.setRemoteDescription = setRemoteDescription;
    }
  }

  if (proto.createOffer) {
    var _origCreateOffer = proto.createOffer;
    var createOffer = function createOffer(options) {
      return _origCreateOffer.apply(this, arguments).then(function(offer) {
        if (offer && offer.sdp) {
          offer = new RTCSessionDescription({
            type: offer.type,
            sdp: sanitizeSDP(offer.sdp)
          });
        }
        return offer;
      });
    };
    if (window._safelyOverrideValue) {
      window._safelyOverrideValue(proto, 'createOffer', createOffer);
    } else {
      proto.createOffer = createOffer;
    }
  }

  if (proto.createAnswer) {
    var _origCreateAnswer = proto.createAnswer;
    var createAnswer = function createAnswer(options) {
      return _origCreateAnswer.apply(this, arguments).then(function(answer) {
        if (answer && answer.sdp) {
          answer = new RTCSessionDescription({
            type: answer.type,
            sdp: sanitizeSDP(answer.sdp)
          });
        }
        return answer;
      });
    };
    if (window._safelyOverrideValue) {
      window._safelyOverrideValue(proto, 'createAnswer', createAnswer);
    } else {
      proto.createAnswer = createAnswer;
    }
  }

  var descProp = Object.getOwnPropertyDescriptor(proto, 'localDescription');
  if (descProp && descProp.get) {
    var _origLocalDescGet = descProp.get;
    var localDescriptionGetter = function localDescription() {
      var desc = _origLocalDescGet.apply(this);
      if (desc && desc.sdp) {
        return new RTCSessionDescription({
          type: desc.type,
          sdp: sanitizeSDP(desc.sdp)
        });
      }
      return desc;
    };
    if (window._safelyOverrideGetter) {
      window._safelyOverrideGetter(proto, 'localDescription', localDescriptionGetter);
    } else {
      Object.defineProperty(proto, 'localDescription', {
        get: localDescriptionGetter,
        configurable: true
      });
    }
  }

  var iceProp = Object.getOwnPropertyDescriptor(proto, 'onicecandidate');
  if (iceProp && iceProp.set) {
    var _origIceSet = iceProp.set;
    var handlers = new WeakMap();
    Object.defineProperty(proto, 'onicecandidate', {
      get: function onicecandidate() {
        return handlers.get(this) || null;
      },
      set: function onicecandidate(handler) {
        var wrapped = function(event) {
          if (event && event.candidate && isLeakyCandidate(event.candidate)) {
            return;
          }
          if (handler) handler.call(this, event);
        };
        handlers.set(this, handler);
        _origIceSet.call(this, wrapped);
      },
      configurable: true,
      enumerable: true
    });
    if (window._makeNative) {
      var getDesc = Object.getOwnPropertyDescriptor(proto, 'onicecandidate');
      window._makeNative(getDesc.get, 'get onicecandidate');
      window._makeNative(getDesc.set, 'set onicecandidate');
    }
  }

  if (proto.addEventListener) {
    var _origAddEvt = proto.addEventListener;
    var addEventListenerFunc = function addEventListener(type, listener, opts) {
      if (type === 'icecandidate') {
        var wrapped = function(event) {
          if (event && event.candidate && isLeakyCandidate(event.candidate)) {
            return;
          }
          listener.call(this, event);
        };
        return _origAddEvt.call(this, type, wrapped, opts);
      }
      return _origAddEvt.apply(this, arguments);
    };
    if (window._safelyOverrideValue) {
      window._safelyOverrideValue(proto, 'addEventListener', addEventListenerFunc);
    } else {
      proto.addEventListener = addEventListenerFunc;
    }
  }

  if (window._safelyOverrideValue) {
    window._safelyOverrideValue(window, 'RTCPeerConnection', PatchedRTC);
    if (window.webkitRTCPeerConnection) {
      window._safelyOverrideValue(window, 'webkitRTCPeerConnection', PatchedRTC);
    }
  } else {
    window.RTCPeerConnection = PatchedRTC;
    if (window.webkitRTCPeerConnection) {
      window.webkitRTCPeerConnection = PatchedRTC;
    }
  }
})();
