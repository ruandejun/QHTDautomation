// MunAntiBrowser - Network Information Spoof
// Fakes navigator.connection with randomized values.

(function fakeNetwork() {
  function doUpdateProp(obj, prop, newVal){
    let props = Object.getOwnPropertyDescriptor(obj, prop) || {configurable:true};
    props["value"] = newVal;
    props["configurable"] = true;
    Object.defineProperty(obj, prop, props);
    return props;
  }

  var seed = {{plugins_seed}} || 12345;
  function seededRandom() {
    var x = Math.sin(seed++) * 10000;
    return x - Math.floor(x);
  }

  var rand = function(max){
    return Math.floor(seededRandom() * max);
  };
  var randArr = function(arr){
    return arr[Math.floor(seededRandom() * arr.length)];
  };

  let NetworkInformation = function(){
    this.downlink = rand(10) || 1.5;
    this.downlinkMax = Infinity;
    this.effectiveType = "4g";
    this.rtt = randArr([50, 75, 100, 125, 150]);
    this.saveData = false;
    this.type = randArr(["wifi", "ethernet", "other"]);
    this.onchange = null;
    this.ontypechange = null;
    this.__proto__ = NetworkInformation;
  };

  let fakeNet = new NetworkInformation();
  fakeNet.addEventListener = function(){};
  doUpdateProp(navigator, "connection", fakeNet);
})();
