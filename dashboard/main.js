(function() {
    Handlebars.registerHelper('formatPrice',function(aPrice) {
        if(typeof aPrice === "number")
            return aPrice.toFixed(1);
        else
            return "";
    });
    Handlebars.registerHelper('formatTime',function(aTime) {
        if(typeof aTime === "number" && aTime > 100000) {
            var date= new Date();
            date.setTime(aTime*1000);
            return date.toLocaleString();
        } else
            return "";
    });
    Handlebars.registerHelper('classFromPosition',function(aPos) {
        var clazz= aPos.status;
        if(aPos.amount > 0) {
            clazz +="Long";
        } else {
            clazz += "Short";
        }
        return clazz;
    });

})();

function refresh() {
    $.getJSON('dashboard.json', function(data) {
        var template = Handlebars.templates.openPositions;
        var container= $('#positions')[0];
        container.innerHTML= '';
        for (let id in data) {
            var bot= data[id];
            bot.id= id;
            var totalPos= 0;
            bot.positions.forEach(function(pos) {
                if(pos.status == "open") {
                    totalPos += pos.amount;
                }
            });
            bot.totalPos = totalPos;
            var div= template(bot);
            container.insertAdjacentHTML('beforeend',div);
        }
    });
}