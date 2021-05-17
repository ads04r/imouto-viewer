var map;

function homeScreen()
{
    $(".content-wrapper").load("./stats.html", function(){ initialiseGraphics(); });
}

function anniversaryScreen()
{
    $(".content-wrapper").load("./onthisday.html", function(){ initialiseGraphics(); });
}

function uploadScreen()
{
    $(".content-wrapper").load("./upload.html", function(){

	window.setInterval(updateUploadStats, 1000);
	window.setInterval(updateUploadQueue, 5000);
	updateUploadStats();
	updateUploadQueue();

    });
}

function updateUploadQueue()
{
    var url = "/location-manager/import";

    $.ajax({
        url: url,
        dataType: 'json',
        method: 'GET',
        success: function(data) {

		var tasks = data.tasks;
		var html = "";

		for(i = 0; i < tasks.length; i++)
		{
			var item = tasks[i];
			var dt = new Date(item.time * 1000);
			var filename = item.parameters[0][0];
			var source = item.parameters[0][1];
			var path = filename.split('/');

			html = html + '<div class="post">';
			html = html + '<div class="user-block">';
			html = html + '<span class="username no-image">' + path[path.length - 1] + ' [' + source + ']</span>';
			html = html + '<span class="description no-image">' + dt.toLocaleString() + '</span>';
			html = html + '</div>';
			html = html + '</div>';
		}

		$("#import-queue").html(html);
        }
    });
}

function updateUploadStats()
{
    var url = "/location-manager/process";

    $.ajax({
        url: url,
        dataType: 'json',
        method: 'GET',
        success: function(data) {

		var ps = new Date(data.stats['last_calculated_positon'] * 1000);
		var ev = new Date(data.stats['last_generated_event'] * 1000);

		$('#stats-last-position').html(ps.toLocaleString());
		$('#stats-last-event').html(ev.toLocaleString());

        }
    });
}

function onMapClick(e)
{
    var RES = 100000;
    var lat = Math.round(e.latlng.lat * RES) / RES;
    var lon = Math.round(e.latlng.lng * RES) / RES;
    
    $('#id_lat').val(lat);
    $('#id_lon').val(lon);
}

function timelineScreen()
{
    $(".content-wrapper").load("./timeline.html", function()
    {
        $("#event-delete-button").on('click', function()
        {
            var id="#li_event_" + $("#delete-id").val();
            var url="events/" + $("#delete-id").val() + "/delete";

            $(id).remove();
            $("#timeline_event_delete").modal('hide');

            $.ajax({
                url: url,
                dataType: 'json',
                method: 'POST',
                success: function(data) { }
            });
            
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

function updateReportYearSelect()
{
	var year = $('#generate-life-report-year').val();
	$('#id_label').val(year);
	$('#new-report-generate-year').val(year);
}

function reportsScreen()
{
    $(".content-wrapper").load("./reports.html", function(){
        updateReportYearSelect();
        $("#generate-life-report-year").on('change', function() {
            updateReportYearSelect();
        });
        $("#report-save-form-button").on('click', function(){
            $("#report-edit").submit();
        });
    });
}

function reportScreen(id)
{
    $(".content-wrapper").load("./reports/" + id + ".html", function(){
        makeMap();
    });
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
           contentHeight: "auto",

        });
        $("#event-save-form-button").on('click', function()
        {
            $("form#event-edit").submit();
            
            return false;
        })

    });
}

function dayScreen(id)
{
    $(".content-wrapper").load("./days/" + id + ".html", function(){ });
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
        
        var lat = 50.9;
        var lon = -1.4;
        var map = L.map('mapselect', {center: [lat, lon], zoom: 13});
        L.tileLayer('{{ tiles }}', {
            attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
            maxZoom: 16
        }).addTo(map);
        $('#id_lat').val(lat);
        $('#id_lon').val(lon);
        map.on('click', onMapClick);
        
        // The following block is required because we've foolishly put a leaflet map in a tab in a modal.
        $("a[href='#loc']").on('shown.bs.tab', function() 
        {
            map.invalidateSize();
        });
        
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
    
    $(".time-chart").each(function()
    {
        var data = $(this).data('data');
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

        $("#timeline-event-save-form-button").on('click', function()
        {
            $("form#timeline-event-edit").submit();
            
            return false;
        })
        $("a.eventedit").on('click', function()
        {
            var id = $(this).data('event-id');
            var caption = $(this).data('event-label');
            var type = $(this).data('event-type');
            var description = $(this).data('event-description');
            $("#timeline-event-edit").attr('action', 'events/' + id + '.html');
            $("#id_caption").val(caption);
            $("#id_type").val(type);
            $("#id_description").val(description);

            $("#timeline_event_edit").modal();
            return false;
        });
        $("a.eventdelete").on('click', function()
        {
            var id = $(this).data('event-id');
            $("#delete-id").val(id);

            $("#timeline_event_delete").modal('show');

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
            if($(this).hasClass('reportmap'))
            {
                var map = L.map(id, { zoomControl: false });
            } else {
                var map = L.map(id);
            }
            L.geoJSON(data).addTo(map);
            L.tileLayer('{{ tiles }}', {
                attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
                maxZoom: 16, minZoom: 2
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
            if(legend[i].indexOf('%') !== -1) { sleep = 1; }
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
                    var hours = parseInt(tooltipItem.value / (60 * 60));
                    var minutes = parseInt(tooltipItem.value / 60);
                    var ret = "";

                    if (hours > 0)
                    {
                        ret = hours + ' hours';
                    } else {
                        ret = minutes + ' minutes';
                    }
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
        L.tileLayer('{{ tiles }}', {
            attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/" target="_top">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/" target="_top">CC-BY-SA</a>',
            maxZoom: 16
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

function eventPeopleDeleteName(id)
{
	$('.person_delete').each(function() {
		if($(this).data('id') == id) { $(this).remove(); }
	});
	return false;
}

function eventScreen(id)
{
    $(".content-wrapper").load("./events/" + id + ".html", function()
    {
        
        makeMap();
        initialiseGraphics();
        $("#event-save-form-button").on('click', function()
        {
            $("form#event-edit").submit();
            
            return false;
        });
	$("#person_add_submit").on('click', function()
	{
		var id = $('#person_add').val();
		var label = $('#person_add').find("option[value='" + id + "']").text();
		var html = '<div class="person_delete" data-id="' + id + '">';
		html = html + label + ' ';
		html = html + '<small><a class="delete_person" href="#" data-id="' + id + '">Delete</a></small>'
		html = html + '</div>';
		$('#event_people_list').append(html);
		$('.delete_person').off('click');
		$('.delete_person').on('click', function() { return eventPeopleDeleteName($(this).data('id')); });
	});
	$('.delete_person').on('click', function() { return eventPeopleDeleteName($(this).data('id')); });
	$('#event-people-save-form-button').on('click', function() {
		var data = [];
		$('.person_delete').each(function() {
			data.push($(this).data('id'));
		});
		$('<form method="POST" action="./add-people-to-event"><input type="hidden" id="id" name="id" value="' + id + '"/><input type="hidden" id="people" name="people" value="' + data.join('|') + '"/></form>').appendTo('body').submit();
		return false;
	});

    });
}

function search(query, callback)
{
            var url = './search.json';
            var data = {'query': query};
            $.ajax({
                url: url,
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify(data),
                method: 'POST',
                success: callback
            });
}

function typingDelay(callback, ms)
{
        var timer = 0;
        return function()
        {
                var context = this, args = arguments;
                clearTimeout(timer);
                timer = setTimeout(function()
                {
                        callback.apply(context, args);
                }, ms || 0);
        }
}

function pageRefresh()
{
    var page = window.location.hash.replace('#', '');
    var loading = '<section class="content"><div class="container-fluid"><div class="row"><div class="col-xs-1 col-sm-3 col-md-5"></div><div class="col-xs-10 col-sm-6 col-md-2"><div class="box box-primary"><div class="box-body text-center"><i class="fa fa-spin fa-refresh"></i>&nbsp;Loading</div></div></div></div></div></section>';
    
    $("#imouto-search-text").on('keydown', function() { $("#imouto-search-results").html(''); });
    $("#imouto-search-text").on('keyup', typingDelay(function()
    {
        var text = $(this).val();
        if(text == '') { return; }
        search(text, function(data)
        {
            var html = '';
            for(i = 0; i < data.length; i++)
            {
                item = data[i];
                html = html + '<li><a href="#' + item.link + '">';
                if(item.link.startsWith('person')) { html = html + '<i class="menu-icon fa fa-user-o bg-gray"></i>'; }
                if(item.link.startsWith('place')) { html = html + '<i class="menu-icon fa fa-map-marker bg-gray"></i>'; }
                if(item.link.startsWith('event'))
                {
                    switch(item.type) {
                    case 'life_event':
                        html = html + '<i class="menu-icon fa fa-calendar bg-gray"></i>';
                        break;
                    case 'loc_prox':
                        html = html + '<i class="menu-icon fa fa-map-marker bg-blue"></i>';
                        break;
                    case 'journey':
                        html = html + '<i class="menu-icon fa fa-road bg-green"></i>';
                        break;
                    case 'sleepover':
                        html = html + '<i class="menu-icon fa fa-moon-o bg-green"></i>';
                        break;
                    case 'photo':
                        html = html + '<i class="menu-icon fa fa-camera bg-orange"></i>';
                        break;
                    default:
                        html = html + '<i class="menu-icon fa fa-calendar bg-gray"></i>';
                    }
                }
                html = html + '<div class="menu-info"><h4 class="control-sidebar-subheading">' + item.label + '</h4><p>' + item.description + '</p></div></a></li>';
            }
            $("#imouto-search-results").html('<ul class="control-sidebar-menu">' + html + '</ul>');
        });
    }, 500));
    $(".content-wrapper").html(loading);
    
    if(page == '') { homeScreen(); return true; }
    if(page == 'timeline') { timelineScreen(); return true; }
    if(page == 'files') { uploadScreen(); return true; }
    if(page == 'reports') { reportsScreen(); return true; }
    if(page == 'onthisday') { anniversaryScreen(); return true; }

    if(page == 'events') { eventsScreen(); return true; }
    if(page == 'people') { peopleScreen(); return true; }
    if(page == 'places') { placesScreen(); return true; }
                                        
    if(page.startsWith('day_')) { dayScreen(page.replace('day_', '')); }
    if(page.startsWith('event_')) { eventScreen(page.replace('event_', '')); }
    if(page.startsWith('place_')) { placeScreen(page.replace('place_', '')); }
    if(page.startsWith('person_')) { personScreen(page.replace('person_', '')); }
    if(page.startsWith('report_')) { reportScreen(page.replace('report_', '')); }
                            
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
