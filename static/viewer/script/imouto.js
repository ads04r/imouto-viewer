var map;

function homeScreen()
{
    $(".content-wrapper").load("./stats.html", function(){ initialiseGraphics(); });
}

function timelineScreen()
{
    $(".content-wrapper").load("./timeline.html", function()
    {
        $("#event-delete-button").on('click', function()
        {
            var id="#li_event_" + $(this).data('id');
            console.log("Deleting " + id);
            $(id).remove();
            $("#timeline_event_delete").modal('hide');
        });
        
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
    $(".content-wrapper").load("./events.html", function()
    {

        var date = new Date();
        var d = date.getDate(),
            m = date.getMonth(),
            y = date.getFullYear();
        $('#calendar').fullCalendar({
           header: {
               left: 'prev,next today',
               center: 'title',
               right: 'month,agendaWeek,agendaDay'
           },
           buttonText: {
               today: 'today',
               month: 'month',
               week: 'week',
               day: 'day'
           },
           events: {
               url: 'events.json'
           },
           editable: false,
           droppable: false, // this allows things to be dropped onto the calendar !!!

        });

    });
}

function peopleScreen()
{
    $(".content-wrapper").load("./people.html", function(){ });
}

function personScreen(id)
{
    $(".content-wrapper").load("./people/" + id + ".html", function(){ });
}

function placesScreen(id)
{
    $(".content-wrapper").load("./places.html", function(){
        $(".save-form-button").on('click', function()
        {
            $("#place-add").submit();
            return true;
        });
    });
}

function placeScreen(id)
{
    $(".content-wrapper").load("./places/" + id + ".html", function(){ makeMap(); });
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
    
    $(".line-chart").each(function()
    {
        var data = $(this).data('data').split(',');
        makeLineChart($(this)[0].getContext('2d'), data);
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

        $("a.eventedit").on('click', function()
        {
            $("#timeline_event_edit").modal();
            return false;
        });
        $("a.eventdelete").on('click', function()
        {
            var id = $(this).data('event-id');
            
            $("#timeline_event_delete").on('show.bs.modal', function(e)
            {
                $("#event-delete-button").attr('data-id', id);

            }).modal();

            return false;
        });
        makeMap();
        
        if($('body').height() <= $(window).height()) { loadTimelineSegment(); }
    });
}

function makeMap()
{
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
}

function makeLineChart(lineChartCanvas, data)
{
    var labels = []
    for(i = 0; i < data.length; i++)
    {
        labels.push(i);
    }
    var lineChart = new Chart(lineChartCanvas);
    var config = {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    backgroundColor: '#0073b7',
                    data: data,
                    fill: true,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            tooltips: { enabled: false },
            legend: {
                display: false
            },
            scales: {
                xAxes: [
                    { 
                        display: false
                    }
                ],
                yAxes: [
                    { 
                        display: true
                    }
                ]
            },
            maintainAspectRatio: true
        }
    }
    lineChart = new Chart(lineChartCanvas, config);
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
        
        makeMap();
        initialiseGraphics();

    });
}


function pageRefresh()
{
    var page = window.location.hash.replace('#', '');
    var loading = '<section class="content"><div class="container-fluid"><div class="row"><div class="col-xs-1 col-sm-3 col-md-5"></div><div class="col-xs-10 col-sm-6 col-md-2"><div class="box box-primary"><div class="box-body text-center"><i class="fa fa-spin fa-refresh"></i>&nbsp;Loading</div></div></div></div></div></section>';
    
    $(".content-wrapper").html(loading);
    
    if(page == '') { homeScreen(); return true; }
    if(page == 'timeline') { timelineScreen(); return true; }
    if(page == 'reports') { reportsScreen(); return true; }

    if(page == 'events') { eventsScreen(); return true; }
    if(page == 'people') { peopleScreen(); return true; }
    if(page == 'places') { placesScreen(); return true; }
                                        
    if(page.startsWith('event_')) { eventScreen(page.replace('event_', '')); }
    if(page.startsWith('place_')) { placeScreen(page.replace('place_', '')); }
    if(page.startsWith('person_')) { personScreen(page.replace('person_', '')); }
                            
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
