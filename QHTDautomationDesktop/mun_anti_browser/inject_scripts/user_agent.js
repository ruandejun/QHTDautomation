// MunAntiBrowser - User Agent Spoof (v2)
// Overrides ALL navigator properties that reveal browser/OS identity.
// Template: {{UserAgent}}

(function fakeUserAgent() {
  'use strict';

  var ua = '{{UserAgent}}';

  // 1. navigator.userAgent
  try {
    Object.defineProperty(navigator, 'userAgent', {
      get: function() { return ua; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // 2. navigator.appVersion (derived from UA)
  try {
    var appVer = ua.indexOf('Mozilla/') === 0 ? ua.substring(8) : ua;
    Object.defineProperty(navigator, 'appVersion', {
      get: function() { return appVer; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // 3. navigator.vendor (Chrome = "Google Inc.", Firefox = "", Safari = "Apple Computer, Inc.")
  try {
    Object.defineProperty(navigator, 'vendor', {
      get: function() { return 'Google Inc.'; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // 4. navigator.vendorSub
  try {
    Object.defineProperty(navigator, 'vendorSub', {
      get: function() { return ''; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // 5. navigator.productSub (Chrome/Safari = "20030107")
  try {
    Object.defineProperty(navigator, 'productSub', {
      get: function() { return '20030107'; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // 6. navigator.appName
  try {
    Object.defineProperty(navigator, 'appName', {
      get: function() { return 'Netscape'; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // 7. navigator.product
  try {
    Object.defineProperty(navigator, 'product', {
      get: function() { return 'Gecko'; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // 8. navigator.appCodeName
  try {
    Object.defineProperty(navigator, 'appCodeName', {
      get: function() { return 'Mozilla'; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

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

    var uaData = {
      brands: [
        {brand: 'Chromium', version: chromeVer},
        {brand: 'Google Chrome', version: chromeVer},
        {brand: 'Not-A.Brand', version: '24'}
      ],
      mobile: isMobile,
      platform: platform,
      getHighEntropyValues: function(hints) {
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
      },
      toJSON: function() {
        return {
          brands: uaData.brands,
          mobile: uaData.mobile,
          platform: platform
        };
      }
    };

    Object.defineProperty(navigator, 'userAgentData', {
      get: function() { return uaData; },
      configurable: true, enumerable: true
    });
  } catch(e) {}
})();
