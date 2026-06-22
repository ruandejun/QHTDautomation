// MunAntiBrowser - Battery API Spoof
// Fakes navigator.getBattery with randomized battery level.

(function fakeBattery() {
  var seed = {{plugins_seed}} || 12345;
  function seededRandom() {
    var x = Math.sin(seed++) * 10000;
    return x - Math.floor(x);
  }

  let setting_level = Math.floor(seededRandom() * 50 + 50) / 100;

  function doUpdateProp(obj, prop, newVal){
    let props = Object.getOwnPropertyDescriptor(obj, prop) || {configurable:true};
    props["value"] = newVal;
    props["configurable"] = true;
    Object.defineProperty(obj, prop, props);
    return props;
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

  doUpdateProp(navigator, "getBattery", function() {
    return BatteryPromise;
  });
  doUpdateProp(navigator.getBattery, "toString", "function getBattery() { [native code] }");
})();
