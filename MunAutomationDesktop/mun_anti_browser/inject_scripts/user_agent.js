// MunAntiBrowser - User Agent Spoof (v3)
// Overrides ALL navigator properties that reveal browser/OS identity.
// IMPORTANT: All overrides go on Navigator.prototype, NOT on navigator instance.
// Native Chrome only has getters on the prototype; having instance-level getters
// is a detectable anti-detect fingerprint.
// Template: {{UserAgent}}

(function fakeUserAgent() {
  'use strict';

  var ua = '{{UserAgent}}';

  // Helper: use global _safelyOverrideGetter (defined in cloudflare_bypass.js)
  // which registers getters via _makeNative for toString() spoofing.
  var _safelyOverrideGetter = window._safelyOverrideGetter || function(obj, prop, val) {
    var fn = typeof val === 'function' ? val : function() { return val; };
    if (window._makeNative) { window._makeNative(fn, 'get ' + prop); }
    Object.defineProperty(obj, prop, { get: fn, configurable: true, enumerable: true });
  };

  // 1. navigator.userAgent
  _safelyOverrideGetter(Navigator.prototype, 'userAgent', ua);

  // 2. navigator.appVersion (derived from UA)
  var appVer = ua.indexOf('Mozilla/') === 0 ? ua.substring(8) : ua;
  _safelyOverrideGetter(Navigator.prototype, 'appVersion', appVer);

  // 3. navigator.vendor (Chrome = "Google Inc.", Firefox = "", Safari = "Apple Computer, Inc.")
  _safelyOverrideGetter(Navigator.prototype, 'vendor', 'Google Inc.');

  // 4. navigator.vendorSub
  _safelyOverrideGetter(Navigator.prototype, 'vendorSub', '');

  // 5. navigator.productSub (Chrome/Safari = "20030107")
  _safelyOverrideGetter(Navigator.prototype, 'productSub', '20030107');

  // 6. navigator.appName
  _safelyOverrideGetter(Navigator.prototype, 'appName', 'Netscape');

  // 7. navigator.product
  _safelyOverrideGetter(Navigator.prototype, 'product', 'Gecko');

  // 8. navigator.appCodeName
  _safelyOverrideGetter(Navigator.prototype, 'appCodeName', 'Mozilla');

  // 9. navigator.userAgentData (Client Hints API)
  // Must be consistent with UA string
  try {
    var chromeMatch = ua.match(/Chrome\/([0-9]+)/);
    var chromeVer = chromeMatch ? chromeMatch[1] : '109';
    var isMobile = /Mobile|Android|iPhone/.test(ua);

    // Determine platform from UA
    var platform = 'Windows';
    if (ua.indexOf('Mac OS X') !== -1 || ua.indexOf('Macintosh') !== -1) platform = 'macOS';
    else if (ua.indexOf('Linux') !== -1 && ua.indexOf('Android') === -1) platform = 'Linux';
    else if (ua.indexOf('CrOS') !== -1) platform = 'Chrome OS';
    else if (ua.indexOf('Android') !== -1) platform = 'Android';
    else if (ua.indexOf('iPhone') !== -1 || ua.indexOf('iPad') !== -1) platform = 'iOS';

    var getHighEntropyValuesFn = function(hints) {
      return Promise.resolve({
        brands: uaData.brands,
        mobile: uaData.mobile,
        platform: platform,
        platformVersion: platform === 'Windows' ? '10.0.0' : 
                        platform === 'macOS' ? '13.0.0' :
                        platform === 'Linux' ? '6.1.0' : '14909.100.0',
        architecture: isMobile ? '' : 'x86',
        bitness: isMobile ? '' : '64',
        model: '',
        uaFullVersion: chromeVer + '.0.0.0',
        fullVersionList: [
          {brand: 'Chromium', version: chromeVer + '.0.5414.75'},
          {brand: 'Google Chrome', version: chromeVer + '.0.5414.75'},
          {brand: 'Not-A.Brand', version: '24.0.0.0'}
        ],
        wow64: false
      });
    };
    if (window._makeNative) {
      window._makeNative(getHighEntropyValuesFn, 'getHighEntropyValues');
    }

    var toJSONFn = function() {
      return {
        brands: uaData.brands,
        mobile: uaData.mobile,
        platform: platform
      };
    };
    if (window._makeNative) {
      window._makeNative(toJSONFn, 'toJSON');
    }

    var uaData = {
      brands: [
        {brand: 'Chromium', version: chromeVer},
        {brand: 'Google Chrome', version: chromeVer},
        {brand: 'Not-A.Brand', version: '24'}
      ],
      mobile: isMobile,
      platform: platform,
      getHighEntropyValues: getHighEntropyValuesFn,
      toJSON: toJSONFn
    };

    _safelyOverrideGetter(Navigator.prototype, 'userAgentData', function() { return uaData; });
  } catch(e) {}
})();
