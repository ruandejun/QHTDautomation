// MunAntiBrowser - Media Devices Anonymize
// Removes device IDs from enumerateDevices to prevent camera/mic fingerprinting.

(function fakeMediaDevices() {
  try {
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
      var originalEnumerate = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
      Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {
        value: function() {
          return originalEnumerate().then(function(devices) {
            return devices.map(function(device) {
              return {
                kind: device.kind,
                label: device.label ? device.label.split(' ')[0] : '',
                deviceId: '',
                groupId: ''
              };
            });
          });
        },
        configurable: true, writable: true
      });
    }
  } catch(e) {}
})();
