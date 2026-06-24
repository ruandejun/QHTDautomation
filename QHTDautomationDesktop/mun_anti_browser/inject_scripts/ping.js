// MunAntiBrowser - SendBeacon Block
// Blocks navigator.sendBeacon to prevent tracking pings.

(function fakePing() {
  if (typeof Navigator === 'undefined' || !Navigator.prototype) {
    return;
  }

  // Capture helpers locally in closure to protect dynamic iframes
  const _localMakeNative = window._makeNative;
  const _localSafelyOverrideValue = window._safelyOverrideValue;

  function patchMethod(obj, prop, newFunc, len) {
    if (len !== undefined) {
      try {
        Object.defineProperty(newFunc, 'length', {
          value: len,
          configurable: true
        });
      } catch(e) {}
    }
    if (_localSafelyOverrideValue) {
      _localSafelyOverrideValue(obj, prop, newFunc);
    } else {
      try {
        Object.defineProperty(newFunc, 'name', {
          value: prop,
          configurable: true
        });
      } catch(e) {}
      if (_localMakeNative) {
        _localMakeNative(newFunc, prop);
      }
      try {
        Object.defineProperty(obj, prop, {
          value: newFunc,
          writable: true,
          configurable: true,
          enumerable: true
        });
      } catch(e) {}
    }
  }

  var sendBeaconFunc = function() {
    return true;
  };

  patchMethod(Navigator.prototype, 'sendBeacon', sendBeaconFunc, 2);
})();

