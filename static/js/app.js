(function(){
  try{
    var v = localStorage.getItem("ch-consent");
    if(!v){ document.getElementById("consent").style.display="block"; }
    document.getElementById("c-ok").onclick=function(){localStorage.setItem("ch-consent","essential");document.getElementById("consent").style.display="none";};
    document.getElementById("c-no").onclick=function(){localStorage.setItem("ch-consent","dismissed");document.getElementById("consent").style.display="none";};
  }catch(e){}
})();
