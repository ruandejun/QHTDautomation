// MunAntiBrowser - Font Enumeration Filter
// Restricts font enumeration to a curated list to prevent font fingerprinting.
// Template: {{fonts}} (JSON array of font names)

(function fakeFonts() {
  function defineobjectproperty(val, e, c, w) {
    return {
      value: val,
      enumerable: !!e,
      configurable: !!c,
      writable: !!w
    };
  }

  var DEFAULT = 'auto';
  var originalStyleSetProperty = CSSStyleDeclaration.prototype.setProperty;
  var originalSetAttrib = Element.prototype.setAttribute;
  var originalNodeAppendChild = Node.prototype.appendChild;
  var FontListToUse = {{fonts}}.map(function(x){ return x.toLowerCase(); });
  var baseFonts = ["default"];
  var keywords = ["inherit", "auto", "default", "!Important"];
  baseFonts.push.apply(baseFonts, FontListToUse);
  baseFonts.push.apply(baseFonts, keywords);

  function getAllowedFontFamily(family) {
    var fonts = family.replace(/"|'/g, '').split(',');
    var allowedFonts = fonts.filter(function(font) {
      if (font && font.length) {
        var normalised = font.trim().toLowerCase();
        for (var allowed of baseFonts)
          if (normalised == allowed) return true;
        for (var allowed of document.fonts.values())
          if (normalised == allowed) return true;
      }
    });
    return allowedFonts.map(function(f){
      var trimmed = f.trim();
      return ~trimmed.indexOf(' ') ? "'" + trimmed + "'" : trimmed;
    }).join(", ");
  }

  function modifiedCssSetProperty(key, val) {
    if (key.toLowerCase() == 'font-family') {
      var allowed = getAllowedFontFamily(val);
      return originalStyleSetProperty.call(this, 'font-family', allowed || DEFAULT);
    }
    return originalStyleSetProperty.call(this, key, val);
  }

  function makeModifiedSetCssText(originalSetCssText) {
    return function modifiedSetCssText(css) {
      var fontFamilyMatch = css.match(/\b(?:font-family:([^;]+)(?:;|$))/i);
      if (fontFamilyMatch && fontFamilyMatch.length == 1) {
        css = css.replace(/\b(font-family:[^;]+(;|$))/i, '').trim();
        var allowed = getAllowedFontFamily(fontFamilyMatch[1]) || DEFAULT;
        if (css.length && css[css.length - 1] != ';')
          css += ';';
        css += "font-family: " + allowed + ";";
      }
      return originalSetCssText.call(this, css);
    };
  }

  var modifiedSetAttribute = (function() {
    var innerModify = makeModifiedSetCssText(function (val) {
      return originalSetAttrib.call(this, 'style', val);
    });
    return function modifiedSetAttribute(key, val) {
      if (key.toLowerCase() == 'style') {
        return innerModify.call(this, val);
      }
      return originalSetAttrib.call(this, key, val);
    };
  })();

  function makeModifiedInnerHTML(originalInnerHTML) {
    return function modifiedInnerHTML(html) {
      var retval = originalInnerHTML.call(this, html);
      recursivelyModifyFonts(this.parentNode);
      return retval;
    };
  }

  function recursivelyModifyFonts(elem) {
    if (elem) {
      if (elem.style && elem.style.fontFamily) {
        modifiedCssSetProperty.call(elem.style, 'font-family', elem.style.fontFamily);
      }
      if (elem.childNodes)
        elem.childNodes.forEach(recursivelyModifyFonts);
    }
    return elem;
  }

  function modifiedAppend(child) {
    child = recursivelyModifyFonts(child);
    return originalNodeAppendChild.call(this, child);
  }

  var success = true;

  function overrideFunc(obj, name, f) {
    try {
      Object.defineProperty(obj.prototype, name, defineobjectproperty(f, true));
    } catch(e) { success = false; }
  }

  function overrideSetter(obj, name, makeSetter) {
    try {
      var current = Object.getOwnPropertyDescriptor(obj.prototype, name);
      current.set = makeSetter(current.set);
      current.configurable = false;
      Object.defineProperty(obj.prototype, name, current);
    } catch(e) { success = false; }
  }

  overrideFunc(Node, 'appendChild', modifiedAppend);
  overrideFunc(CSSStyleDeclaration, 'setProperty', modifiedCssSetProperty);
  overrideFunc(Element, 'setAttribute', modifiedSetAttribute);

  try {
    Object.defineProperty(CSSStyleDeclaration.prototype, "fontFamily", {
      set: function fontFamily(f) {
        modifiedCssSetProperty.call(this, 'font-family', f);
      },
      get: function fontFamily() {
        return this.getPropertyValue('font-family');
      }
    });
  } catch(e) { success = false; }

  overrideSetter(CSSStyleDeclaration, 'cssText', makeModifiedSetCssText);
  overrideSetter(Element, 'innerHTML', makeModifiedInnerHTML);
  overrideSetter(Element, 'outerHTML', makeModifiedInnerHTML);
})();
