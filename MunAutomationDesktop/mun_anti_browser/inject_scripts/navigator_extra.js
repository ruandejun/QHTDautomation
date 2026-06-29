// MunAntiBrowser - Navigator Extra Spoofing (v3)
// Comprehensive navigator/screen/window consistency spoofing.
// iphey.com cross-checks: screen dimensions, color depth, pixel ratio,
// connection info, device memory, battery, and more.

(function fakeNavigatorExtra() {
  'use strict';

  // Helper local fallback if global helpers are not loaded (e.g. in some frame contexts)
  var _safelyOverrideGetter = window._safelyOverrideGetter || function(obj, prop, val) {
    var fn = typeof val === 'function' ? val : function() { return val; };
    Object.defineProperty(obj, prop, { get: fn, configurable: true, enumerable: true });
  };
  var _safelyOverrideValue = window._safelyOverrideValue || function(obj, prop, val) {
    Object.defineProperty(obj, prop, { value: val, writable: true, configurable: true, enumerable: true });
  };

  // ── Device Memory ──
  var seed = {{plugins_seed}} || 12345;
  var memoryValues = [4, 8, 16];
  var fakeMemory = memoryValues[seed % memoryValues.length];
  
  _safelyOverrideGetter(Navigator.prototype, 'deviceMemory', fakeMemory);

  // ── Languages (must be consistent with Accept-Language header) ──
  var langs = Object.freeze(['en-US', 'en']);
  _safelyOverrideGetter(Navigator.prototype, 'languages', function() { return langs; });
  _safelyOverrideGetter(Navigator.prototype, 'language', 'en-US');

  // ── Do Not Track ──
  _safelyOverrideGetter(Navigator.prototype, 'doNotTrack', null);

  // ── Cookie Enabled ──
  _safelyOverrideGetter(Navigator.prototype, 'cookieEnabled', true);

  // ── Max Touch Points (desktop = 0, mobile varies) ──
  var isMobile = /Mobile|Android|iPhone/.test(navigator.userAgent);
  _safelyOverrideGetter(Navigator.prototype, 'maxTouchPoints', isMobile ? 5 : 0);

  // ── document.hasFocus() ──
  _safelyOverrideValue(Document.prototype, 'hasFocus', function() { return true; });

  // ── Screen consistency ──
  // iphey checks: screen.width, screen.height, screen.availWidth, screen.availHeight,
  //   screen.colorDepth, screen.pixelDepth, devicePixelRatio
  try {
    if (typeof screen !== 'undefined' && typeof Screen !== 'undefined') {
      var profileW = {{profile_width}} || 1920;
      var profileH = {{profile_height}} || 1080;

      // Override directly on Screen.prototype for maximum detection avoidance
      _safelyOverrideGetter(Screen.prototype, 'width', function() {
        var currentOuterW = window.outerWidth || window.innerWidth || profileW;
        return Math.max(profileW, currentOuterW);
      });
      _safelyOverrideGetter(Screen.prototype, 'height', function() {
        var currentOuterH = window.outerHeight || window.innerHeight || profileH;
        return Math.max(profileH, currentOuterH);
      });
      _safelyOverrideGetter(Screen.prototype, 'availWidth', function() {
        var currentOuterW = window.outerWidth || window.innerWidth || profileW;
        return Math.max(profileW, currentOuterW);
      });
      _safelyOverrideGetter(Screen.prototype, 'availHeight', function() {
        var currentOuterH = window.outerHeight || window.innerHeight || profileH;
        var sh = Math.max(profileH, currentOuterH);
        return sh - 40; // Trừ đi taskbar
      });
      _safelyOverrideGetter(Screen.prototype, 'availLeft', 0);
      _safelyOverrideGetter(Screen.prototype, 'availTop', 0);

      // Color depth must be consistent (24 for most monitors)
      _safelyOverrideGetter(Screen.prototype, 'colorDepth', 24);
      _safelyOverrideGetter(Screen.prototype, 'pixelDepth', 24);

      // Screen orientation
      _safelyOverrideGetter(Screen.prototype, 'orientation', function() {
        return {
          type: 'landscape-primary',
          angle: 0,
          onchange: null
        };
      });
    }
  } catch(e) {}

  // ── devicePixelRatio consistency ──
  try {
    var dpr = 1;
    var ua = navigator.userAgent || '';
    if (/iPhone|iPad|iPod/.test(ua)) {
      dpr = /iPhone/.test(ua) ? 3 : 2;
    } else if (/Android/.test(ua)) {
      dpr = (seed % 2 === 0) ? 2 : 3;
    } else if (/Macintosh|Mac OS X/.test(ua)) {
      dpr = (seed % 3 === 0) ? 2 : 1;
    }
    _safelyOverrideGetter(window, 'devicePixelRatio', dpr);
    if (typeof Window !== 'undefined') {
      _safelyOverrideGetter(Window.prototype, 'devicePixelRatio', dpr);
    }
  } catch(e) {}

  // ── window dimensions consistency ──
  try {
    var profileW = {{profile_width}} || 1920;
    var profileH = {{profile_height}} || 1080;
    
    // We REMOVE outerWidth/outerHeight static overrides to let them default to native window dimensions.
    // This maintains perfect innerWidth <= outerWidth <= screen.width consistency.
    
    // innerWidth/innerHeight = viewport (minus scrollbar/toolbars)
    if (window.innerWidth === 0 || window.innerHeight === 0) {
      _safelyOverrideGetter(window, 'innerWidth', profileW);
      _safelyOverrideGetter(window, 'innerHeight', profileH - 85);
      if (typeof Window !== 'undefined') {
        _safelyOverrideGetter(Window.prototype, 'innerWidth', profileW);
        _safelyOverrideGetter(Window.prototype, 'innerHeight', profileH - 85);
      }
    }
    
    // screenX/screenY
    _safelyOverrideGetter(window, 'screenX', 0);
    _safelyOverrideGetter(window, 'screenY', 0);
    _safelyOverrideGetter(window, 'screenLeft', 0);
    _safelyOverrideGetter(window, 'screenTop', 0);
    if (typeof Window !== 'undefined') {
      _safelyOverrideGetter(Window.prototype, 'screenX', 0);
      _safelyOverrideGetter(Window.prototype, 'screenY', 0);
      _safelyOverrideGetter(Window.prototype, 'screenLeft', 0);
      _safelyOverrideGetter(Window.prototype, 'screenTop', 0);
    }
  } catch(e) {}

  // ── Visibility API ──
  try {
    Object.defineProperty(document, 'hidden', {
      get: function() { return false; },
      configurable: true
    });
    Object.defineProperty(document, 'visibilityState', {
      get: function() { return 'visible'; },
      configurable: true
    });
  } catch(e) {}

  // ── Performance.memory (Chrome-specific) ──
  try {
    if (typeof performance !== 'undefined') {
      var memGB = fakeMemory * 1073741824;
      Object.defineProperty(performance, 'memory', {
        get: function() {
          return {
            jsHeapSizeLimit: memGB,
            totalJSHeapSize: Math.floor(memGB * 0.7),
            usedJSHeapSize: Math.floor(memGB * 0.3)
          };
        },
        configurable: true
      });
    }
  } catch(e) {}

  // ── Connection API consistency ──
  try {
    if (navigator.connection) {
      Object.defineProperty(navigator.connection, 'effectiveType', {
        get: function() { return '4g'; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(navigator.connection, 'rtt', {
        get: function() { return 50; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(navigator.connection, 'downlink', {
        get: function() { return 10; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(navigator.connection, 'saveData', {
        get: function() { return false; },
        configurable: true, enumerable: true
      });
    }
  } catch(e) {}

  // ── Notification permission safe check ──
  try {
    if (typeof Notification !== 'undefined' && navigator.permissions && navigator.permissions.query) {
      var origQuery = navigator.permissions.query.bind(navigator.permissions);
      var queryProxy = function(parameters) {
        if (parameters && parameters.name === 'notifications') {
          return Promise.resolve({
            state: Notification.permission || 'default',
            onchange: null
          });
        }
        return origQuery(parameters);
      };
      if (window._makeNative) {
        window._makeNative(queryProxy, 'query');
      }
      navigator.permissions.query = queryProxy;
    }
  } catch(e) {}

  // ── Iframe contentWindow consistency ──
  // Some detectors check if properties differ inside iframes
  try {
    var origContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
    // Don't override - just ensure consistency is maintained
  } catch(e) {}

})();
