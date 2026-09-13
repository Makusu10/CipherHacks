(function(){
  // typing loop for hero terminal teaser (original lines, no external deps)
  var el = document.getElementById("px-type");
  if(el){
    var lines = ["$ help  →  3 boxes online", "$ scan 10.13.0.5  →  80/tcp open", "$ submit flag{scan_read_think}  →  +100 XP"];
    var li = 0, ci = 0, out = "";
    function tick(){
      var cur = lines[li];
      ci++;
      el.textContent = out + cur.slice(0, ci) + "▊";
      if(ci >= cur.length){
        out += cur + "\n"; ci = 0; li = (li+1) % lines.length;
        if(li === 0){ out = ""; }
        setTimeout(tick, 1100);
      } else setTimeout(tick, 34);
    }
    if(!window.matchMedia("(prefers-reduced-motion: reduce)").matches) tick();
    else el.textContent = lines.join("\n");
  }
  // mascot speech on click/hover
  var bot = document.getElementById("px-bot"), say = document.getElementById("px-say");
  var msgs = ["boop. fictional targets only.", "psst — try 'ls -la' below.", "nice. flags look like flag{...}.", "+100 XP is waiting in Labs."];
  var n = 0;
  function talk(){ if(!say) return; say.textContent = msgs[n % msgs.length]; n++; }
  if(bot){ bot.addEventListener("click", talk); bot.addEventListener("mouseenter", talk); }
})();
