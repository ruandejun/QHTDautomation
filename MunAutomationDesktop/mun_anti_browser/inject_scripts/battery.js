// MunAntiBrowser - Battery API Spoof
// Fakes navigator.getBattery with randomized battery level.

(function fakeBattery() {
  var seed = {{plugins_seed}} || 12345;
  function seededRandom() {
    var x = Math.sin(seed++) * 10000;
    return x - Math.floor(x);
  }

  let setting_level = Math.floor(seededRandom() * 50 + 50) / 100;

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

  let BatteryPromise = new Promise(function(resolve, reject){
    let BatteryManager = function(){
      this.charging = seededRandom() > 0.5;
      this.chargingTime = this.charging ? Infinity : 0;
      this.dischargingTime = this.charging ? 0 : Infinity;
      this.level = setting_level;
      this.onchargingchange = null;
      this.onchargingtimechange = null;
      this.ondischargingtimechange = null;
      this.onlevelchange = null;
    };
    resolve(new BatteryManager());
  });

  var getBatteryFunc = function() {
    return BatteryPromise;
  };

  if (typeof Navigator !== 'undefined' && Navigator.prototype) {
    patchMethod(Navigator.prototype, 'getBattery', getBatteryFunc, 0);
  }
})();

