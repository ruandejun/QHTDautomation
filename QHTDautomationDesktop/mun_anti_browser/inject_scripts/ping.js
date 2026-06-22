// MunAntiBrowser - SendBeacon Block
// Blocks navigator.sendBeacon to prevent tracking pings.

(function fakePing() {
  if (!navigator || !navigator.sendBeacon){
    return;
  }
  function doUpdateProp(obj, prop, newVal){
    let props = Object.getOwnPropertyDescriptor(obj, prop) || {configurable:true};
    if (!props["configurable"]) {
      return;
    }
    props["value"] = newVal;
    Object.defineProperty(obj, prop, props);
    return props;
  }

  doUpdateProp(navigator, "sendBeacon", function() {
    return true;
  });
  doUpdateProp(navigator.sendBeacon, "toString", "function sendBeacon() { [native code] }");
})();
