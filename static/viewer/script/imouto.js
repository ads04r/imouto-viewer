var map;

function homeScreen()
{
    $(".content-wrapper").load("./stats.html", function(){ initialiseGraphics(); });
}

function timelineScreen()
{
    $(".content-wrapper").load("./timeline.html", function()
    {
        $(window).on('scroll', function()
        {
            checkTimelineScroll();
        });
        for(i = 0; i < 10; i++)
        {
            loadTimelineSegment();
        }
    });
}

function reportsScreen()
{
    $(".content-wrapper").load("./reports.html", function(){ });
}

function eventsScreen()
{
    $(".content-wrapper").load("./events.html", function(){ });
}

function placeScreen(id)
{
    $(".content-wrapper").load("./places/" + id + ".html", function(){ });
}

function initialiseGraphics()
{
    $(".bar-chart").each(function()
    {
        var data = $(this).data('data');
        var legend = $(this).data('legend');
        if(!(legend)) { legend = '[]'; }
        makeBarChart($(this)[0].getContext('2d'), data, legend);
    });
}

function checkTimelineScroll()
{
    if($('#next-load').length == 1)
    {
        var elem = $('#next-load').parent();
        var top = $(window).scrollTop();
        var bottom = $(window).height() + top;
        
        var bounds = elem.offset();
        var pos = bounds.top;
        
        if(pos < bottom)
        {
            loadTimelineSegment();
        }
    } else {
        $(window).unbind('scroll');
    }
}

function loadTimelineSegment()
{
    var elem = $('#next-load').parent();
    var id = $('#next-load').data('next');
    var url = "timeline/" + id + ".html";

    $.get(url, function(result)
    {
        var container = elem.parent();
        elem.remove();
        container.append(result);
        
        $('.eventmap').each(function()
        {
            var id = $(this).attr('id');
            var data = $(this).data('geojson');
            
            $(this).data('geojson', '');
            if(data == '') { return true; }
            
            var bb = L.latLngBounds(L.latLng(data.bbox[1], data.bbox[0]), L.latLng(data.bbox[3], data.bbox[2]));
            var map = L.map(id);
            L.geoJSON(data).addTo(map);
            L.tileLayer('https://tiles.flarpyland.com/osm/{z}/{x}/{y}.png', {
                attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
                maxZoom: 18
            }).addTo(map);
            map.fitBounds(bb);
        });
        
        if($('body').height() <= $(window).height()) { loadTimelineSegment(); }
    });
}

function makeBarChart(barChartCanvas, data, legend)
{
    var barChartData = {
        labels: [],
        datasets: []
    };
    var colours = ['#ABC1D8', '#3C8DBC', '#0073B7', '#005C92'];
    var sleep = 0; // bit of a bodge, we want to generate a custom tooltip if this is a sleep graph.

    for(j = 0; j < data[0].value.length; j++)
    {
        barChartData.datasets.push({
            backgroundColor: colours[j],
            data: []
        })
        
        for(i = 0; i < data.length; i++)
        {
            item = data[i];
            if(j == 0) { barChartData.labels.push(item.label); }
            barChartData.datasets[j].data.push(item.value[j]);
        }
    }

    var barChart = new Chart(barChartCanvas);
    var barChartOptions = {
        legend: {
            display: false
        },
        scales: {
            yAxes: [{
                display: false,
                stacked: true,
                ticks: { beginAtZero: true }
            }],
            xAxes: [{
                stacked: true,
            }]
        },
        tooltips: {},
        responsive: true,
        maintainAspectRatio: true
    };

    if(legend.length == barChartData.datasets.length)
    {
        for(i = 0; i < legend.length; i++)
        {
            barChartData.datasets[i].label = legend[i];
            if(legend[i].indexOf('sleep') !== -1) { sleep = 1; }
        }
        barChartOptions.legend.display = true;
    }
        
    barChartOptions.datasetFill = false;
    if(sleep == 1)
    {
        barChartOptions.tooltips = {
            
            callbacks: {
                title: function(tooltipItem, chart)
                {
                    return tooltipItem.label;
                },
                label: function(tooltipItem, chart)
                {
                    var ret = parseInt(tooltipItem.value / (60 * 60)) + ' hours';
                    return ret;
                }
            }
            
        }
    }
    
    barChart = new Chart(barChartCanvas, {type: 'bar', data: barChartData, options: barChartOptions});
}

function initialiseJourneyMap(mapdiv)
{
    var mapid = mapdiv.attr('id');
    var eventid = mapdiv.data('event-id');
    var pinlis = mapdiv.find('span');
    var url = './events/' + eventid + '.json';
    for(var i = 0; i < pinlis.length; i++)
    {
        pins[i] = pinlis[i].dataset;
    }
        mapdiv.html("");
        map = L.map(mapid, {
            center: [50.93540, -1.39638],
            zoom: 13
        });
        L.tileLayer('http://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/" target="_top">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/" target="_top">CC-BY-SA</a>',
            maxZoom: 20
        }).addTo(map);
        $.ajax({
            url: url,
            dataType: 'json',
            success: function(data) {
                var polylinedesc = data['journey'];
                var c = polylinedesc.length;
                var i = 0;
                latlngs = [];
                for(i = 0; i < c; i++)
                {
                    var polyline = L.polyline(polylinedesc[i], {color: '#0000FF'}).addTo(map);
                    latlngs.push(polyline);
                }
                            map.fitBounds(polylinedesc);
            }
        });
}

function eventScreen(id)
{
    $(".content-wrapper").load("./events/" + id + ".html", function()
    {
        var mapdiv = $("#journey-map");
        if(mapdiv.length > 0)
        {
            
            var mapid = mapdiv.attr('id');
            var eventid = mapdiv.data('event-id');
            var pinlis = mapdiv.find('span');
            var url = './events/' + eventid + '.json';
            for(var i = 0; i < pinlis.length; i++)
            {
                pins[i] = pinlis[i].dataset;
            }
                    mapdiv.html("");
                    map = L.map(mapid, {
                        center: [50.93540, -1.39638],
                        zoom: 13
                    });
                    L.tileLayer('http://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/" target="_top">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/" target="_top">CC-BY-SA</a>',
                        maxZoom: 20
                    }).addTo(map);
                    $.ajax({
                        url: url,
                        dataType: 'json',
                        success: function(data) {
                            var polylinedesc = data['journey'];
                            var c = polylinedesc.length;
                            var i = 0;
                            latlngs = [];
                            for(i = 0; i < c; i++)
                            {
                                var polyline = L.polyline(polylinedesc[i], {color: '#0000FF'}).addTo(map);
                                latlngs.push(polyline);
                            }
                                           map.fitBounds(polylinedesc);
                        }
                    });
                    
        }
    });
}


function pageRefresh()
{
    var page = window.location.hash.replace('#', '');
    
    if(page == '') { homeScreen(); return true; }
    if(page == 'timeline') { timelineScreen(); return true; }
    if(page == 'events') { eventsScreen(); return true; }
    if(page == 'reports') { reportsScreen(); return true; }
                    
    if(page.startsWith('event_')) { eventScreen(page.replace('event_', '')); }
    if(page.startsWith('place_')) { placeScreen(page.replace('place_', '')); }
                    
    if(page.startsWith('events_'))
    {
        var ds = page.replace('events_', '');
        $(".content-wrapper").load("./dayevents/" + ds + ".html", function(){ });
    }
}

$(document).ready(function()
{
    $(window).bind('hashchange', function(e) { pageRefresh(); });
    pageRefresh();
});
