// MunAntiBrowser - ClientRects Fingerprint Offset
// Offsets getClientRects and getBoundingClientRect to create unique fingerprint.
// Template: {{rects}} (float offset value)

self['MunAnti_NloJhCLvAOj_func'] = function(frame){
  if (frame === null) {
    return;
  }

  if (!frame['MunAnti_NloJhCLvAOj_done']) {
    (function(frame){
      function doUpdateProp(obj, prop, newVal){
        let props = Object.getOwnPropertyDescriptor(obj, prop) || {configurable:true};
        if (!props["configurable"]) {
          return;
        }
        props["value"] = newVal;
        Object.defineProperty(obj, prop, props);
        return props;
      }

      let off = {{rects}};

      function updatedRect(old, round, overwrite){
        function genOffset(round, val){
          return val + (round ? Math.round(off) : off);
        }

        let temp = overwrite === true ? old : new DOMRect();
        temp.top    = genOffset(round, old.top);
        temp.right  = genOffset(round, old.right);
        temp.bottom = genOffset(round, old.bottom);
        temp.left   = genOffset(round, old.left);
        temp.width  = genOffset(round, old.width);
        temp.height = genOffset(round, old.height);
        temp.x      = genOffset(round, old.x);
        temp.y      = genOffset(round, old.y);
        return temp;
      }

      function getClientRectsProtection(el){
        if (window.location.host === "docs.google.com") return;
        let clientRects = frame[el].prototype.getClientRects;
        doUpdateProp(frame[el].prototype, "getClientRects", function(){
          let rects = clientRects.apply(this, arguments);
          let krect = Object.keys(rects);
          let DOMRectList = function(){};
          let list = new DOMRectList();
          list.length = krect.length;
          for (let i = 0; i < list.length; i++){
            if (krect[i] === "length") continue;
            list[i] = updatedRect(rects[krect[i]], false, false);
          }
          return list;
        });
        doUpdateProp(frame[el].prototype.getClientRects, "toString", function(){
          return "getClientRects() { [native code] }";
        });
      }

      function getBoundingClientRectsProtection(el){
        let boundingRects = frame[el].prototype.getBoundingClientRect;
        doUpdateProp(frame[el].prototype, "getBoundingClientRect", function(){
          let rect = boundingRects.apply(this, arguments);
          if (this === undefined || this === null) return rect;
          return updatedRect(rect, true, true);
        });
        doUpdateProp(frame[el].prototype.getBoundingClientRect, "toString", function(){
          return "getBoundingClientRect() { [native code] }";
        });
      }

      ["Element", "Range"].forEach(function(el){
        if (frame[el] === undefined) return;
        getClientRectsProtection(el);
        getBoundingClientRectsProtection(el);
      });
    })(frame);
  } else {
    frame['MunAnti_NloJhCLvAOj_done'] = true;
  }
};

self['MunAnti_NloJhCLvAOj_func'](window);

// Apply to iframes
["HTMLIFrameElement", "HTMLFrameElement"].forEach(function(el) {
  var wind = self[el].prototype.__lookupGetter__('contentWindow'),
      cont = self[el].prototype.__lookupGetter__('contentDocument');

  Object.defineProperties(self[el].prototype, {
    contentWindow: {
      get: function(){
        if (this.src && this.src.indexOf('//') !== -1 && location.host !== this.src.split('/')[2]) return wind.apply(this);
        let frame = wind.apply(this);
        if (frame) self['MunAnti_NloJhCLvAOj_func'](frame);
        return frame;
      }
    },
    contentDocument: {
      get: function(){
        if (this.src && this.src.indexOf('//') !== -1 && location.host !== this.src.split('/')[2]) return cont.apply(this);
        let frame = cont.apply(this);
        if (frame) self['MunAnti_NloJhCLvAOj_func'](frame);
        return frame;
      }
    }
  });
});
