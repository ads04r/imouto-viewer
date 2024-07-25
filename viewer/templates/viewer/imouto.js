{% load static %}var map;
var quiz;
var quiz_score_a;
var quiz_score_d;

var timers = [];

function createTimer(callback, delay)
{
	var x = window.setInterval(callback, delay);
	timers.push(x)
}

function clearTimers()
{
	while(timers.length > 0)
	{
		var x = timers.pop();
		window.clearInterval(x);
	}
}

function errorPage(e)
{
    var err = e.responseText;
    err = err.replace(/^.*<table>/, '<table>');
    err = err.replace(/<\/table>.*$/, '</table>');

    var html = '<section class="content">';
    html = html + '<div class="container-fluid">';
    html = html + '<div class="row">';
    html = html + '<div class="col-xs-12">';
    html = html + '<div class="box box-primary">';
    html = html + '<div class="box-body with-border">';

    if(err.length > 0)
    {
        html = html + err;
    } else {
        html = html + '<h1>Error ' + e.status + '</h1>';
        html = html + '<p>' + e.statusText + '</p>';
    }

    html = html + '</div>';
    html = html + '</div>';
    html = html + '</div>';
    html = html + '</div>';
    html = html + '</div>';
    html = html + '</section>'
    $(".content-wrapper").html(html);
}

function homeScreen()
{
    $(".content-wrapper").load("./stats.html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        initialiseGraphics();
    });
}

function anniversaryScreen()
{
    $(".content-wrapper").load("./onthisday.html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        initialiseGraphics();
    });
}

function lifeGridScreen()
{
    $(".content-wrapper").load("./life_grid.html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }


	$("input.life-grid-category").on('change', function(){
		var c = $(this).data('category');
		var checked = $(this).is(':checked');
		$('td.category-' + c).each(function(){
			var cols = $(this).data('colours').split(',');
			var i;
			for(i = 0; i < cols.length; i++)
			{
				var t = cols[i].split('|');
				if(t.length == 2)
				{
					if(t[0] == c)
					{
						if(checked)
						{
							$(this).css('background-color', t[1]);
						} else {
							$(this).css('background-color', '');
						}
					}
				}
			}
		});
	});
    });
}

function uploadScreen()
{
    $(".content-wrapper").load("./upload.html", function(response, status, xhr){

        if(status == 'error') { errorPage(xhr); return false; }

	$('#watcheddir-save-form-button').on('click', function() {
		$('#watcheddir-edit').submit();
	});
	$('.delete-watched-directory').on('click', function() {
		var id = $(this).data('wd-id');
		var label = $(this).data('wd-label');
		var url = "watched_directory/" + id + ".html";
		var form = $('#delete-wd-form');
		$('#wd-update-id').val(id);
		$('#wd-update-label').html(label);
		form.attr('action', url);
		$('#delete-wd').modal('show');
		$('.delete-wd-button').on('click', function() {
			form.submit();
		});
	});
	createTimer(updateUploadStats, 1000);
	createTimer(updateUploadQueue, 5000);
	updateUploadStats();
	updateUploadQueue();

    });
}

function importWebScreen()
{
    $(".content-wrapper").load("./import-web.html", function(response, status, xhr){

        if(status == 'error') { errorPage(xhr); return false; }

	$('#importformurl').on('keypress', function(e)
	{
		var key = e.which;
		console.log(key);
		if(key == 13) { $('a#importfromweb').click(); return false; }
	});

	$('#importfromweb').on('click', function()
	{
		var url = $('#importformurl').val();
		var waittext = '<tr class="founddata" data-data="{}"><td><i class="fa fa-refresh fa-spin"></i> Loading...</td></tr>';
		$('table#founddata-table').html(waittext);
		importrdf(url, function(data)
		{
			items = [];
			for(var i = 0; i < data.length; i++)
			{
				var item = data[i];
				if(item.label)
				{
					var title = item.label[0];
					if(item.type == 'Location') { title = '<i class="fa fa-map-marker"></i> ' + title; }
					if(item.type == 'Person') { title = '<i class="fa fa-user"></i> ' + title; }
					var elemtd = $("<td>" + title + "</td>");
					var elemtr = $("<tr>", {'class': 'founddata', 'data-data': JSON.stringify(item)});
					elemtr.append(elemtd);
					items.push(elemtr);
				}
			}
			if(items.length == 0) { $('table#founddata-table').html('<tr class="founddata" data-data="{}"><td>No data found.</td></tr>'); } else { $('table#founddata-table').html(''); }
			for(var i = 0; i < items.length; i++)
			{
				$('table#founddata-table').append(items[i]);
			}
			$('.founddata').on('click', function(){
				var data = $(this).data('data');
				if(data != '')
				{
					var label = '';
					var html = '';
					for(var i in data)
					{
						if(i == 'type') { continue; }
						if(i.startsWith('wiki')) { continue; }
						html = html + '<tr><td>' + i + '</td><td>';
						for(var j = 0; j < data[i].length; j++)
						{
							if(i == 'label') { label = data[i][j]; }
							html = html + data[i][j] + '<br/>';
						}
						html = html + '</td></tr>';
					}
					if(html != '') { $("#import-summary-window").html('<div class="box box-primary"><div class="box-header with-border"><h3 class="box-title">' + label + '</h3></div><div class="box-body no-padding"><table class="table table-condensed">' + html + '</table></div></div>'); }
				}
			});
		});
	});

    });
}

function updateReportQueue()
{
	var url = "report_queue.json";

	$.ajax({
		url: url,
		dataType: 'json',
		method: 'GET',
		success: function(data) {

			var html = '';

			for(i = 0; i < data.length; i++)
			{
				var item = data[i];
				var title = '';
				var type = '';
				var task = item.name;
				var icon = '';
				var url = '';

				var task_name = item.name.split('.');

				if(item.error) { icon = '<i class="fa fa-warning text-danger"></i>'; }
				if(item.running) { icon = '<i class="fa fa-play-circle text-success"></i>'; }
				if(item.event)
				{
					title = item.event.caption;
					type = task_name[task_name.length - 1];
					url = '#event_' + item.event.id;
				}
				if(item.report)
				{
					title = item.report.label;
					type = task_name[task_name.length - 1];
					if(item.report.id > 0) { url = '#report_' + item.report.id; }
				}

				html = html + '<tr><td>' + icon + '</td><td>' + title + '<br><small>' + type + '</small></td><td>';
				if(url.length > 0) { html = html + '<a class="btn btn-primary btn-xs eventlink" href="' + url + '">Read&nbsp;more</a>'; }
				html = html + '</td></tr>';
			}

			if(html.length > 0) { html = '<div class="box"><div class="box-header"><h3 class="box-title">In progress</h3></div><div class="box-body no-padding"><table class="table table-condensed">' + html + '</table></div></div>'; }

			$("#report-queue").html(html);

		}
	});
}

function updateUploadQueue()
{
    var url = "import";

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
			var running = item.running;
			var error = item.has_error;

			html = html + '<div class="post">';
			html = html + '<div class="user-block">';
			if(running){ html = html + '<span class="pull-right"><span class="badge" style="background-color: #007F00;">RUNNING</span></span>'; }
			if(error){ html = html + '<span class="pull-right"><span class="badge" style="background-color: #FF0000;">ERROR</span></span>'; }
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
    var url = "process";

    $.ajax({
        url: url,
        dataType: 'json',
        method: 'GET',
        success: function(data) {

		var ps = new Date(data.stats['last_calculated_position'] * 1000);
		var ev = new Date(data.stats['last_generated_event'] * 1000);

		$('#stats-last-position').html(ps.toLocaleString());
		$('#stats-last-event').html(ev.toLocaleString());

        }
    });
}

function onLocEventMapClick(e)
{
    var RES = 100000;
    var lat = Math.round(e.latlng.lat * RES) / RES;
    var lon = Math.round(e.latlng.lng * RES) / RES;
    var canvas = $('#location_event_select');
    var slug = canvas.data('date').replace('day_', '')
    var url = 'days/' + slug + '/locevents.json';
    var data = {}
    var csrf = $('input[name="csrfmiddlewaretoken"]').val();

    canvas.html('<i class="fa fa-refresh fa-spin"></i>');
    data['lat'] = lat
    data['lon'] = lon

    $.ajax({
        url: url,
        dataType: 'json',
        contentType: 'application/json',
        data: JSON.stringify(data),
        method: 'POST',
        success: function(data) {
            var html = '';
            for(i = 0; i < data.length; i++) {
                item = data[i];
                html = html + '<tr class="loceventadd">'
                html = html + '<td data-start="' + item.start_time + '" data-end="' + item.end_time + '" data-text="' + item.text + '" style="width: 100%;">' + item.display_text + '</td>';
                html = html + '<td class="pull-right"><input data-text="' + item.text + '" data-location="' + item.location + '" data-start="' + item.start_time + '" data-end="' + item.end_time + '" class="locationeventselect" type="checkbox"/></td>';
                html = html + '</tr>';
            }
            if(html == '')
            {
                html = '<p>No events found in this location.</p>';
            } else {
                html = '<div class="table-responsive"><table class="table no-margin">' + html + '</table></div>'
            }
            canvas.html(html);
            $('#addlocationevent').off('click');
            $('#addlocationevent').on('click', function() {
                var canvas = $('#location_event_select');
                var url = 'days/' + slug + '/createlocevents.json';
                var jsondata = [];
                $('tr.loceventadd').each(function()
		{
			var item = {};
			var c = $(this).find("input.locationeventselect");
			item['start'] = c.data('start');
			item['end'] = c.data('end');
			item['text'] = c.data('text');
			item['location'] = c.data('location');
			item['value'] = c.prop('checked');
	                jsondata.push(item);
		});
                $.ajax({
                    url: url,
                    dataType: 'json',
                    contentType: 'application/json',
                    data: JSON.stringify(jsondata),
                    method: 'POST',
                    success: function(data)
			{
				if(data.length == 0) { alert("Please select one or more events to create."); return false; }
				window.location.reload(false);
			}
                });
                return false;
            });
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
    $(".content-wrapper").load("./timeline.html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }

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

function updateReportYearSelect(year)
{
	$('#id_label').val(year);
	$('#new-report-generate-year').val(year);
}

function reportsScreen()
{
    $(".content-wrapper").load("./reports.html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        var year = $("#generate-life-report-year").val();
        updateReportYearSelect(year);
        $(document).on('change', "#generate-life-report-year", function() {
            var year = $(this).val();
            updateReportYearSelect(year);
        });
        $("#report-save-form-button").on('click', function(){
            $("#report-edit").submit();
        });
        $(".report-delete-form-button").on('click', function(){

            var id = $(this).data('report-id');
            var url = "reports/" + id + "/delete";

            $("#report_box_" + id).remove();
            $("#admin_report_delete_" + id).modal('hide');

            $.ajax({
                url: url,
                dataType: 'json',
                method: 'POST',
                success: function(data) { }
            });
        });
	createTimer(updateReportQueue, 5000);
	updateReportQueue();
    });
}

function reportScreen(id, page='misc')
{
    var url = "./reports/" + id + ".html";
    if(page.length > 0) { url = "./reports/" + id + "/" + page + ".html"; }
    $(".content-wrapper").load(url, function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        $('.report-graph').each(function() {
            var canvas = $(this);
            var type = canvas.data('type');
            var data = canvas.data('data');
            if(type == 'donut') { makeDonutChart(canvas[0].getContext('2d'), data[1], data[0]); }
        });
        makeMap();
    });
}

function questionIndexScreen()
{
    var url = "./questionnaires.html";
    $(".content-wrapper").load(url, function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        $("#q-save-form-button").on('click', function(){
            $("#q-edit").submit();
        });
        $(".q-delete-form-button").on('click', function(){

            var id = $(this).data('q-id');
            var url = "questionnaires/" + id + "/delete";

            $("#q_box_id_" + id).remove();
            $("#admin_q_delete_" + id).modal('hide');

            $.ajax({
                url: url,
                dataType: 'json',
                method: 'POST',
                success: function(data) { }
            });
        });
    });
}

function questionEditScreen(id)
{
    var url = "./questionnaires/" + id + ".html";
    $(".content-wrapper").load(url, function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        $('#questionnairesubmit').on('click', function(){
            $('#questionnaireform').submit();
        });
    });
}

function array_shuffle(array)
{
	for (var i = array.length - 1; i > 0; i--)
	{
		var j = Math.floor(Math.random() * (i + 1));
		var temp = array[i];
		array[i] = array[j];
		array[j] = temp;
	}
}

function dayHeartReport(date)
{
	$("#dayheartsummary").html('<i class="fa fa-refresh fa-spin"></i>');

	var url = './days/' + date + '/heart.json';
        $.ajax({
            url: url,
            method: 'GET',
            success: function(data) {

		var html = "";
		html = html + "<div class=\"btn-group pull-right\">";
		html = html + "<button data-date=\"" + data.prev + "\" class=\"btn btn-default heartdaylink\">Previous</button>";
		if(data.next) { html = html + "<button data-date=\"" + data.next + "\" class=\"btn btn-default heartdaylink\">Next</button>"; }
		else { html = html + "<button class=\"btn btn-default disabled\">Next</button>"; }
		html = html + "</div>";

		html = html + "<h4><a href=\"#day_" + date + "\">" + data.date + "</a></h4>";

		html = html + "<div class=\"container-fluid\">";
		html = html + "<div class=\"row\">";
		html = html + "<div class=\"col-xs-12 col-sm-6 col-md-9\">";

		if(data.heart){

			html = html + "<p>Daily Heart Activity</p>";

			var hsecs = data.heart.heartzonetime[1];
			var hmins = parseInt(parseFloat(hsecs) / 60.0);

			hsecs = hsecs - (hmins * 60);
			var hlabel = String(hmins) + " minutes, " + String(hsecs) + " seconds";
			if(hsecs == 0)
			{ hlabel = String(hmins) + " minutes"; }

			html = html + "<div class=\"table-responsive\">";
			html = html + "<table class=\"table no-margin\">";
			html = html + "<tr><td>Highest heart rate:</td><td>" + data.heart.day_max_rate + "</td></tr>";
			html = html + "<tr><td>Time in optimal zone:</td><td>" + hlabel + "</td></tr>";
			html = html + "</table>";
			html = html + "</div>";

		} else {

			html = html + "<p>No heart information exists about this day.</p>";

		}

		html = html + "</div>";
		html = html + "<div class=\"col-xs-12 col-sm-6 col-md-3\">";

		if(data.heart){
			html = html + '<canvas id="heartdonut" style="height: 160px;">';
		}

		html = html + "</div>";
		html = html + "</div>";
		html = html + "<div class=\"row\">";
		html = html + "<div class=\"col-xs-12 col-sm-12 col-md-12\">";

		if(data.heart){
			if(data.heart.graph){
				html = html + '<canvas id="hearthistory"/>';
			}
		}

		html = html + "</div>";
		html = html + "</div>";
		html = html + "</div>";

		$("#dayheartsummary").html(html);

		if(data.heart){
			var context = $("#heartdonut");
			makeDonutChart(context[0].getContext('2d'), data.heart.heartzonetime, ['no zone', 'above 50% of max', 'above 70% of max']);
			if(data.heart.graph){
				var morecontext = $("#hearthistory");
				makeLineChart(morecontext[0].getContext('2d'), data.heart.graph, '#3C8DBC', true);
			}
		}
		$("button.heartdaylink").on('click', function() { var ds = $(this).data('date'); dayHeartReport(ds); return false; });
            }
        });

}

function daySleepReport(date)
{
	$("#daysleepsummary").html('<i class="fa fa-refresh fa-spin"></i>');

	var date = $(this).data('day');
	var url = './days/' + date + '/sleep.json';
        $.ajax({
            url: url,
            method: 'GET',
            success: function(data) {

		var html = "";
		html = html + "<div class=\"btn-group pull-right\">";
		html = html + "<button data-date=\"" + data.prev + "\" class=\"btn btn-default sleepdaylink\">Previous</button>";
		if(data.next) { html = html + "<button data-date=\"" + data.next + "\" class=\"btn btn-default sleepdaylink\">Next</button>"; }
		else { html = html + "<button class=\"btn btn-default disabled\">Next</button>"; }
		html = html + "</div>";

		html = html + "<h4><a href=\"#day_" + date + "\">" + data.date + "</a></h4>";

		html = html + "<div class=\"container-fluid\">";
		html = html + "<div class=\"row\">";
		html = html + "<div class=\"col-xs-12 col-sm-6 col-md-9\">";

		if(data.sleep){

			html = html + "<p>Sleep pattern</p>";

			html = html + "<div class=\"progress-group\">";
			html = html + "<div class=\"progress sleep-bar\">";
			for(var i = 0; i < data.sleep.data.length; i++)
			{
				var item = data.sleep.data[i];
				html = html + "<div class=\"progress-bar\" role=\"progressbar\" aria-valuenow=\"" + item[2] + "\" aria-valuemin=\"0\" aria-valuemax=\"100\" style=\"width: " + item[2] + "%; background-color:";
				if(item[0] == 0)
				{
					html = html + "rgba(0, 0, 0, 0)";
				}
				if(item[0] == 1)
				{
					html = html + "#ABC1D8";
				}
				if(item[0] == 2)
				{
					html = html + "#3C8DBC";
				}
				html = html + "\"></div>";
			}
			html = html + "</div>";
			html = html + "</div>";

			html = html + "<div style=\"width: 100%;\">";
			html = html + "<div class=\"pull-right\">" + data.sleep.end_friendly + "</div>";
			html = html + "<div class=\"pull-left\">" + data.sleep.start_friendly + "</div>";
			html = html + "</div>";

			html = html + "<br/>";
			html = html + "<div class=\"pull-right\">";
			html = html + "<span style=\"margin-left: 1em; white-space: nowrap;\"><i class=\"fa fa-square-o\"></i>&nbsp;Awake</span>";
			html = html + "<span style=\"margin-left: 1em; white-space: nowrap;\"><i style=\"color: #ABC1D8;\" class=\"fa fa-square\"></i>&nbsp;Light&nbsp;sleep</span>";
			html = html + "<span style=\"margin-left: 1em; white-space: nowrap;\"><i style=\"color: #3C8DBC;\" class=\"fa fa-square\"></i>&nbsp;Deep&nbsp;sleep</span>";
			html = html + "</div>";

		} else {

			html = html + "<p>No sleep information exists about this day.</p>";

		}

		html = html + "</div>";
		html = html + "<div class=\"col-xs-12 col-sm-6 col-md-3\">";

		if(data.wake_up){
			html = html + "<div class=\"table-responsive\">";
			html = html + "<table class=\"table no-margin\">";
			html = html + "<tr><td>Wake up:</td><td>" + data.wake_up_local + "</td></tr>";
			if(data.bedtime){
				html = html + "<tr><td>Bed time:</td><td>" + data.bedtime_local + "</td></tr>";
				html = html + "<tr><td>Wake time:</td><td>" + Math.floor(data.length / (60 * 60)) + " hours</td></tr>";
			}
			html = html + "</table>";
			html = html + "</div>";
		}

		html = html + "</div>";
		html = html + "</div>";
		html = html + "</div>";


		$("#daysleepsummary").html(html);
		$("button.sleepdaylink").on('click', function() { var ds = $(this).data('date'); daySleepReport(ds); return false; });
            }
        });

}

function healthReportScreen(page)
{
    $(".content-wrapper").load("./health/" + page + ".html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
	if(page == 'exercise')
	{
		$('.cmd-delete-exercise').on('click', function(e)
		{
			var id = $(this).data('id');
			var label = $(this).data('label');
			var events = parseInt($(this).data('events'));
		        var url="workout/" + id + "/delete";

			$('#workout-delete-warning').html('Are you sure you want to delete "' + label + '"?');
			$('#workout-delete-subwarning').html('<small>This workout type contains ' + events + ' events.</small>');
			$("#admin_workout_delete").modal('show');

		        $("#workout-delete-button").on('click', function()
		        {

		            $.ajax({
		                url: url,
		                dataType: 'json',
		                method: 'POST',
		                success: function(data) { window.location.reload(false); }
		            });

		        });

			return false;
		});

		$('#workout-save-form-button').on('click', function(e)
		{
	            $("#workout-edit").submit();
		});
	}
        if(page == 'heart')
        {
            var dt = new Date();
            dt.setDate(dt.getDate() - 1);
            var dsy = String(dt.getFullYear());
            var dsm = String(dt.getMonth() + 1);
            var dsd = String(dt.getDate());
            var ds = dsy + dsm.padStart(2, '0') + dsd.padStart(2, '0');
            dayHeartReport(ds);
        }
        if(page == 'sleep')
        {
        }
        if(page == 'mentalhealth')
        {
        }
        $("#data-submit-button").on('click', function()
        {
            var url = $("form").attr('action');
            var data = {}
            $("form input").each(function() {
                k = $(this).attr('name');
                v = $(this).val();
                if(!(k === undefined)) { data[k] = v; }
            });
            $("form select").each(function() {
                k = $(this).attr('name');
                v = $(this).val();
                if(!(k === undefined)) { data[k] = v; }
            });
            $.ajax({
                url: url,
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify(data),
                method: 'POST',
                success: function() {
                    window.location.reload(false);
                }
            });
            return false;
        });
        initialiseGraphics();
    });
}

function eventsScreen()
{
    $(".content-wrapper").load("./events.html", function(response, status, xhr)
    {

        if(status == 'error') { errorPage(xhr); return false; }

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
           dayClick: function(date, jsEvent, view) {
               url = "#day_" + date.format("YYYYMMDD");
               window.location = url;
           }

        });
        $("#event-save-form-button").on('click', function()
        {
            $("form#event-edit").submit();
            return false;
        })
        $("#period-save-form-button").on('click', function(){
            $("#period-edit").submit();
            return false;
        });
        var colpicker = new JSColor($("#id_colour")[0], {});
	//colpicker.show();

    });
}

function updateReportStatus()
{
    var id = $("#year-report-generation-progress").data('year');
    $("#year-report-generation-progress").load("./years/progress/" + id + ".html", function(response, status, xhr)
    {
	$(".add-year-report").on('click', function()
	{
            $("#createyearreport").modal('show');
            return false;
	});
    });
}

function yearScreen(id)
{
    $(".content-wrapper").load("./years/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }
        $('.report-graph').each(function() {
            var canvas = $(this);
            var type = canvas.data('type');
            var data = canvas.data('data');
            if(type == 'donut') { makeDonutChart(canvas[0].getContext('2d'), data[1], data[0]); }
        });
        $("#addyearstatsubmit").on('click', function() { $("#addyearstatform").submit(); return false; });
        $('.addyearstat').on('click', function() {
          var category = $(this).data('category');
          $("#statcategoryid").val(category);
          $("#statname").val("");
          $("#statvalue").val("");
          $("#stattext").val("");
          $("#addyearstat").modal('show');
          return false;
        });
        initialiseGraphics();
        $('#generateyearpdfsubmit').on('click', function() { $('#generateyearpdfform').submit(); return false; });
        createTimer(updateReportStatus, 1000);
	updateReportStatus()
    });
}

function monthScreen(id)
{
    $(".content-wrapper").load("./months/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }
        initialiseGraphics();
        makeMap();
    });
}

function dayScreen(id)
{
    $(".content-wrapper").load("./days/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }

        $("a.eventdelete").on('click', function()
        {
            var id = $(this).data('event-id');
            $("#delete-id").val(id);

            $("#timeline_event_delete").modal('show');

            return false;
        });

        $("#event-delete-button").on('click', function()
        {
            var id="#day_event_" + $("#delete-id").val();
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

        daySummary(id);
        makeMap();

        var lat = {{ home.lat }};
        var lon = {{ home.lon }};
        var map = L.map('mapselect', {center: [lat, lon], zoom: 13});
        L.tileLayer('{{ tiles }}', {
            attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
            maxZoom: 16
        }).addTo(map);
        //$('#id_lat').val(lat);
        //$('#id_lon').val(lon);
        map.on('click', onLocEventMapClick);

        // The following block is required because we've foolishly put a leaflet map in a tab in a modal.
        $("#day_locevent_add").on('shown.bs.modal', function() 
        {
            map.invalidateSize();
        });

        $("#event-save-form-button").on('click', function()
        {
            $("form#event-edit").submit();
            return false;
        })

	activateImageEditor();

    });
}

function daySummary(date)
{
        $.ajax({
            url: './days/' + date + '/weight.json',
            method: 'GET',
            success: function(data) {

		var html = "";

		if(data.length > 0){

			html = html + "<div class=\"box box-primary\">";
			html = html + "<div class=\"box-body\">";

			html = html + "<p>Weigh-ins</p>";

			html = html + "<div class=\"table-responsive\">";
			html = html + "<table class=\"table no-margin\">";

			html = html + "<tr><th>Time</th><th>Weight</th></tr>";
			for(var i = 0; i < data.length; i++)
			{
				var item = data[i];
				html = html + "<tr><td>" + item.time + "</td><td>" + item.weight + "kg</td></tr>";
			}

			html = html + "</table>";
			html = html + "</div>";

			html = html + "</div>";
			html = html + "</div>";

		}

		if(html != '') { $(".day-weight-summary").html(html); }
            }
        });
        $.ajax({
            url: './days/' + date + '/heart.json',
            method: 'GET',
            success: function(data) {

		var html = "";

		if(data.heart){

			html = html + "<div class=\"box box-primary\">";
			html = html + '<div class="box-header"><h3 class="box-title">Daily Heart Activity</h3></div>';
			html = html + "<div class=\"box-body\">";

			var hsecs = data.heart.heartzonetime[1];
			var hmins = parseInt(parseFloat(hsecs) / 60.0);

			hsecs = hsecs - (hmins * 60);
			var hlabel = String(hmins) + " minutes, " + String(hsecs) + " seconds";
			if(hsecs == 0)
			{ hlabel = String(hmins) + " minutes"; }

			hslabel = '' + String(hsecs);
			if(hslabel.length < 2) { hslabel = '0' + hslabel; }
			hslabel = String(hmins) + ':' + hslabel;

			html = html + "<div class=\"table-responsive\">";
			html = html + "<table class=\"table no-margin\">";
			html = html + "<tr><td>Highest heart rate:</td><td>" + data.heart.day_max_rate + "</td></tr>";
			html = html + "<tr><td>Time in optimal zone:</td><td><span class=\"hidden-xs hidden-sm hidden-md\">" + hlabel + "</span><span class=\"hidden-lg hidden-xl\">" + hslabel + "</span></td></tr>";
			html = html + "</table>";
			html = html + "</div>";

			html = html + "</div>";
			html = html + "</div>";

		}

		if(html != '') { $(".day-heart-summary").html(html); }
            }
        });
        $.ajax({
            url: './days/' + date + '/sleep.json',
            method: 'GET',
            success: function(data) {
		var html = "";
		var mood = $(".day-stats").data('mood');

		if(data.wake_up_local){
			html = html + '<table class="table no-margin">';
			html = html + "<tr>";
			html = html + "<td>Wake up:</td>";
			html = html + "<td>" + data.wake_up_local + "</td>";
			html = html + "</tr>";
			if(data.bedtime_local){
				html = html + "<tr>";
				html = html + "<td>Bedtime:</td>";
				html = html + "<td>" + data.bedtime_local + "</td>";
				html = html + "</tr>";
			}
			if(mood){
				var mood_icon = 'smile-o';
				if(mood <= 4) { mood_icon = 'meh-o'; }
				if(mood <= 2) { mood_icon = 'frown-o'; }
				html = html + "<tr>";
				html = html + "<td>Mood:</td>";
				html = html + "<td>";
				for(var i = 0; i < mood; i++)
				{
					html = html + '<i class="fa fa-' + mood_icon + '"></i>&nbsp;';
				}
				html = html + "</td>";
				html = html + "</tr>";
			}
			html = html + "</table>";
			$(".day-stats").html(html);
		}

		html = "";

		if(data.sleep){

			html = html + '<div class=\"box box-primary\">';
			html = html + '<div class="box-header"><h3 class="box-title">Sleep pattern</h3></div>';
			html = html + '<div class=\"box-body\">';

			html = html + "<div class=\"progress-group\">";
			html = html + "<div class=\"progress sleep-bar\">";
			for(var i = 0; i < data.sleep.data.length; i++)
			{
				var item = data.sleep.data[i];
				html = html + "<div class=\"progress-bar\" role=\"progressbar\" aria-valuenow=\"" + item[2] + "\" aria-valuemin=\"0\" aria-valuemax=\"100\" style=\"width: " + item[2] + "%; background-color:";
				if(item[0] == 0)
				{
					html = html + "rgba(0, 0, 0, 0)";
				}
				if(item[0] == 1)
				{
					html = html + "#ABC1D8";
				}
				if(item[0] == 2)
				{
					html = html + "#3C8DBC";
				}
				html = html + "\"></div>";
			}
			html = html + "</div>";
			html = html + "</div>";

			html = html + "<div style=\"width: 100%;\">";
			html = html + "<div class=\"pull-right\">" + data.sleep.end_friendly + "</div>";
			html = html + "<div class=\"pull-left\">" + data.sleep.start_friendly + "</div>";
			html = html + "</div>";

			html = html + "<br/>";
			html = html + "<div class=\"pull-right\">";
			html = html + "<span style=\"margin-left: 1em; white-space: nowrap;\"><i class=\"fa fa-square-o\"></i>&nbsp;Awake</span>";
			html = html + "<span style=\"margin-left: 1em; white-space: nowrap;\"><i style=\"color: #ABC1D8;\" class=\"fa fa-square\"></i>&nbsp;Light&nbsp;sleep</span>";
			html = html + "<span style=\"margin-left: 1em; white-space: nowrap;\"><i style=\"color: #3C8DBC;\" class=\"fa fa-square\"></i>&nbsp;Deep&nbsp;sleep</span>";
			html = html + "</div>";

			html = html + "</div>";

			if(data.sleep.mid_wakes)
			{

				html = html + '<div class="box-footer">';
				html = html + '<h5 class="box-title">Wake periods</h5>';
				html = html + '<table class="table table-condensed">';
				for(i = 0; i < data.sleep.mid_wakes.length; i++)
				{
					dt = new Date(data.sleep.mid_wakes[i].wake);
					ls = data.sleep.mid_wakes[i].length;
					lm = parseInt(ls / 60);
					ls = ls - (lm * 60);
					html = html + '<tr>';
					html = html + '<td>' + dt.toLocaleTimeString() + '</td>';
					html = html + '<td>' + lm + ' minutes, ' + ls + ' seconds</td>';
					html = html + '</tr>';
				}
				html = html + '</table>';
				html = html + '</div>';
			}

			html = html + "</div>";
		}

		if(html != '') { $(".day-sleep-summary").html(html); }
            }
        });
        $.ajax({
            url: './days/' + date + '/music.json',
            method: 'GET',
            success: function(data) {

		var html = "";

		if(data.length > 0){

			html = html + "<div class=\"box box-primary\">";
			html = html + "<div class=\"box-body\">";

			html = html + "<p>Today's Music</p>";

			html = html + "<div class=\"table-responsive\">";
			html = html + "<table class=\"table table-sm no-margin\">";

			for(i = 0; i < data.length; i++){
				var artists = '';
				for(j = 0; j < data[i].artists.length; j++)
				{
					if(artists != '') { artists = artists + ', '; }
					artists = artists + data[i].artists[j].name;
				}
				html = html + "<tr><td>" + data[i].time + "</td><td>" + data[i].title + '<br><small class="muted">' + artists + '</small></td></tr>';
			}

			html = html + "</table>";
			html = html + "</div>";

			html = html + "</div>";
			html = html + "</div>";

		}

		if(html != '') { $(".day-music-summary").html(html); }
            }
        });
        $.ajax({
            url: './days/' + date + '/people.json',
            method: 'GET',
            success: function(data) {

		var html = "";
		var i;

		for(i = 0; i < data.length; i++){
			if(data[i].image) { html = html + '<a href="#person_' + data[i].id + '"><img class="img-circle img-bordered-sm" width="50" height="50" src="people/' + data[i].id + '_thumb.jpg"></a>'; }
		}

		if(html != '') { $(".day-people-summary").html(html); }
            }
        });
}

function peopleScreen()
{
    $(".content-wrapper").load("./people.html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }
        $(".save-form-button").on('click', function()
        {
            $("#person-add").submit();
            return true;
        });
    });
}

function personScreen(id)
{
    $(".content-wrapper").load("./people/" + id + ".html", function(response, status, xhr){
        if(status == 'error')
        {
            errorPage(xhr);
            return false;
        }
        $(".save-form-button").on('click', function()
        {
            $("#person-add").submit();
            return true;
        });
        activateImageEditor();
    });
}

function placesScreen(id)
{
    $(".content-wrapper").load("./places.html", function(response, status, xhr){

        if(status == 'error') { errorPage(xhr); return false; }

        var lat = {{ home.lat }};
        var lon = {{ home.lon }};
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
    $(".content-wrapper").load("./places/" + id + ".html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        makeMap();
        initialiseGraphics();
        $(".save-form-button").on('click', function()
        {
            $("#place-add").submit();
            return true;
        });
    });
}

function placeCategoryScreen(id)
{
    $(".content-wrapper").load("./places/categories/" + id + ".html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        $(".save-form-button").on('click', function()
        {
            $("#placecat-add").submit();
            return true;
        });
    });
}

function cityScreen(id)
{
    $(".content-wrapper").load("./cities/" + id + ".html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        makeMap();
    });
}

function countryScreen(id)
{
    $(".content-wrapper").load("./countries/" + id + ".html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
    });
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
        makeLineChart($(this)[0].getContext('2d'), data, '#3C8DBC');
    });
    
    $(".line-chart-irregular").each(function()
    {
        var data = $(this).data('data');
        makeLineChart($(this)[0].getContext('2d'), data, '#3C8DBC');
    });
    
    $(".time-chart").each(function()
    {
        var data = $(this).data('data');
        makeLineChart($(this)[0].getContext('2d'), data, '#0073b7');
    });
    
    $(".scatter-chart").each(function()
    {
        var data = $(this).data('data');
        makeScatterChart($(this)[0].getContext('2d'), data, '#0073b7');
    });
    
    $(".donut-chart").each(function()
    {
        var data = $(this).data('data');
        var labels = $(this).data('labels');
        makeDonutChart($(this)[0].getContext('2d'), data, labels);
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

function activateImageEditor()
{
	$('.event_image_select').on('click', function() {
		var html = '';
		var photoid = $(this).data('photoid');
		var eventid = $(this).data('eventid');
		var locid = $(this).data('photolocationid');
		var loc = $(this).data('photolocation');
		var dateid = $(this).data('photodateid');
		var photodate = $(this).data('photodate');
		var phototime = $(this).data('phototime');
		var cover_image = $(this).data('cover');
		var img = $(this).html();
		var alt = $('img', this).attr('alt');
		html = html + '<table class="table">';
		html = html + '<tr>';
		html = html + '<td id="event_photo_image">' + img + '</td>';
		if(eventid)
		{
			html = html + '<td>';
			html = html + '<form role="form" id="photo-form" method="POST" action="photo/' + photoid + '.json">';
			html = html + '<div class="form-group">';
			html = html + '<label for="form-input-image-caption">Image Caption</label>';
			html = html + '<input id="form-input-image-caption" name="image_caption" class="form-control" type="text" placeholder="Image caption" value="' + alt + '"/>';
			html = html + '</div>';
			html = html + '<div class="checkbox">';
			html = html + '<label>';
			if(cover_image) { html = html + '<input type="checkbox" name="event_cover_image" checked="checked"/>'; } else { html = html + '<input type="checkbox" name="event_cover_image"/>'; }
			html = html + 'Event Cover Image';
			html = html + '</label>';
			html = html + '</div>';
			html = html + '<input type="hidden" name="event_id" value="' + eventid + '"/>';
			html = html + '<input type="hidden" name="photo_id" value="' + photoid + '"/>';
			html = html + '</form>';
			html = html + '</td>';
		} else {
			html = html + '<td>';
			html = html + '<h4 class="box-title">' + alt + '</h4>';
			if(dateid) { html = html + '<p>Taken on ' + photodate + ' at ' + phototime + '</p>'; }
			if(locid) { html = html + '<p>Taken at ' + loc + '</p>'; }
			html = html + '';
			html = html + '';
			html = html + '';
			html = html + '</td>';
		}
		html = html + '</tr>';
		html = html + '</table>';
		$('#admin_event_photo_body').html(html);
		$("#admin_event_photo").modal('show');

		return false;
	});
	$('#event-photo-save-form-button').on('click', function() {
		$('#photo-form').submit();
	});
}

function buildRouteMap(g, m)
{
	if(g.type == 'GeometryCollection'){
		var l = g.geometries.length;
		for(var i = 0; i < l; i++) {
			buildRouteMap(g.geometries[i], m);
		}
	}
	if(g.type == 'MultiLineString')
	{
		var l = L.geoJSON(g);
		l.addTo(m);
	}
	if(g.type == 'Point')
	{
		if(g.properties && g.properties.label)
		{
			var p = L.popup({closeButton: false});
			switch(g.properties.type) {
			case 'stop':
				var l = L.geoJSON(g, {
					pointToLayer: function(f, l) {
						return new L.marker(l, { icon: L.icon({
							iconUrl: '{% static 'viewer/graphics/marker-icon-smlred.png' %}',
							shadowUrl: '{% static 'libraries/leaflet/images/marker-shadow.png' %}',
							iconSize: [25, 41],
							shadowSize: [41, 41],
							iconAnchor: [13, 40],
							shadowAnchor: [13, 40],
							popupAnchor: [0, -20]
						})})
					}
				});
				p.setContent('<p class="map-bubble-text"><i class="fa fa-pause"></i>&nbsp;' + g.properties.label + '</p>');
				break;
			case 'poi':
				var l = L.geoJSON(g, {
					pointToLayer: function(f, l) {

						return new L.circle(l, {
						    color: '#3C8DBC',
						    fillColor: '#ABC1D8',
						    fillOpacity: 0.5,
						    radius: 32
						})
					}
				});
				p.setContent('<p class="map-bubble-text"><i class="fa fa-map-pin"></i>&nbsp;' + g.properties.label + '</p>');
				break;
			default:
				var l = L.geoJSON(g);
				p.setContent('<p class="map-bubble-text">' + g.properties.label + '</p>');
			}
			l.bindPopup(p).addTo(m);
		}
		else
		{
			var l = L.geoJSON(g);
			l.addTo(m);
		}
	}
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
            L.geoJSON(data, {onEachFeature: function(f, l){buildRouteMap(f.geometry, map);}});
            L.tileLayer('{{ tiles }}', {
                attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
                maxZoom: 16, minZoom: 2
            }).addTo(map);
            map.fitBounds(bb);
    });
}

function makeDonutChart(donutChartCanvas, data, labels)
{
    var donutChart = new Chart(donutChartCanvas);
    if(labels.length <= 4)
    {
        var colours = ['#ABC1D8', '#3C8DBC', '#0073B7', '#005C92'];
    } else {
        var colours = ['#FF0000', '#FF7F00', '#FFFF00', '#00FF00', '#00FFFF', '#0000FF', '#7F00FF', '#FF00FF'];
    }
    var config = {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [
                {
                    data: data,
                    backgroundColor: colours
                }
            ]
        },
        options: {
            responsive: true,
            aspectRatio: 0.5,
            maintainAspectRatio: true,
            animation: { animateScale: true, animateRotate: true },
            legend: { display: true, position: 'bottom', align: 'start' },
            tooltips: {
		callbacks: {
			label: function(item, data){
				var ix = item.index;
				var label = data.labels[ix];
				var value = data.datasets[0].data[ix];
				var total = 0;
				for (var i = 0; i < data.datasets[0].data.length; i++) { total = total + data.datasets[0].data[i]; }
				var prc = parseInt((value / total) * 100.0);
				return String(prc) + '% - ' + label;
			}
		}
            }
        }
    };
    donutChart = new Chart(donutChartCanvas, config);
}

function makeSleepAreaChart(canvas, datasets)
{
	var colours = ['#FFFFFF', '#ABC1D8', '#3C8DBC'];
	var labels = ['', ''];
	var fills = [false, 0]
	var data = {
		labels: [],
		datasets: []
	};

	for(var i = 0; i < datasets.length; i++)
	{
		data.labels = Array.apply(null, Array(datasets[i].length)).map(function(x, i) { return i; }),
		data.datasets.push({
			label: labels[i],
			data: datasets[i].map(function(x, i) { return (parseFloat(x) / (60 * 60)); }),
			backgroundColor: colours[i],
			borderColor: colours[2],
			fill: fills[i],
			tension: 0
		});

	}

	var config = {
		type: 'line',
		data: data,
		options: {
			legend: { display: false },
			responsive: true,
			tooltips: {
				callbacks: {
					title: function(item, data) {
						ds = ['Wake up', 'Bedtime'];
						i = item[0].datasetIndex;
						return ds[i];
					},
					label: function(item, data) {
						i = item.yLabel;
						while(i > 12) { i = i - 12; }
						h = String(Math.floor(i));
						m = String(Math.floor((i - h) * 60));
						return h + ':' + (m.padStart(2, '0'));
					}
				}
			},
			scales: {
				yAxes: [{
					ticks: {
						callback: function(value, index, values) {
							ret = value;
							while(ret > 12)
							{
								ret = ret - 12;
							}
							return ret + ':00';
						}
					}
				}],
				xAxes: [{
					ticks: {
						callback: function(value, index, values) {
							return null;
						}
					}
				}]
			}
		}
	};

	var chart = new Chart(canvas, config);
	chart.update();
}

function splitEvent(event, splittime)
{
	var dt = new Date(splittime);
	var ds = dt.toLocaleTimeString();
	document.body.style.cursor = 'default';
	if(splittime.includes(':'))
	{
		$('span.split-time').html(ds);
		$('input#split-time').val(splittime);
		$('#event_split_modal').modal('show');
	}
}

function makeLineChart(lineChartCanvas, data, colstr, timeline=false)
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
                    backgroundColor: colstr,
                    data: data,
                    fill: true,
                    pointRadius: 0,
                    lineTension: 0
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
                        display: timeline,
			type: 'time',
                        distribution: 'linear',
                        bounds: 'data',
                        time: {
                            unit: 'minute',
                            stepSize: 10
                        },
                        ticks: { }
                    }
                ],
                yAxes: [
                    {
                        display: true
                    }
                ]
            },
            maintainAspectRatio: true,
            onClick: function(e, chart) {
		var activeElement = lineChart.getElementAtEvent(e);
                if(activeElement.length >= 1)
                {
                    var ix = activeElement[0]._index;
                    var value = lineChart.data.datasets[0].data[ix];
                    var ref = window.location.hash.replace('#', '').split('_');
                    if((ref.length == 2) && (ref[0] == 'event')) { splitEvent(ref[1], value['x']); }
                }
            }
        }
    }
    if(data.length > 0) { config.options.scales.xAxes[0].ticks.min = data[0].x; }
    lineChart = new Chart(lineChartCanvas, config);
}

function makeScatterChart(lineChartCanvas, data, colstr)
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
                    borderColor: colstr,
                    data: data,
                    fill: false,
                    pointRadius: 4,
                    tension: 0.4
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
                        type: 'time',
                        display: false,
                        ticks: { source: 'data' },
                        time: { min: data[0]['x'], unit: 'month', displayFormats: { month: 'MMM' } }
                    }
                ],
                yAxes: [
                    { 
                        ticks: { precision: 0, z: 50 },
                        display: true
                    }
                ]
            }
        }
    }
    lineChart = new Chart(lineChartCanvas, config);
    lineChart.update();
}

function makeBarChart(barChartCanvas, data, legend)
{
    var barChartData = {
        labels: [],
        datasets: []
    };
    var colours = ['#ABC1D8', '#3C8DBC', '#0073B7', '#005C92'];
    var sleep = 0; // bit of a bodge, we want to generate a custom tooltip if this is a sleep graph.
    var links = [];

    for(j = 0; j < data[0].value.length; j++)
    {
        barChartData.datasets.push({
            backgroundColor: colours[j],
            data: []
        })

        for(i = 0; i < data.length; i++)
        {
            item = data[i];
            if(j == 0)
            {
                barChartData.labels.push(item.label);
                if(item.link)
                {
                    links.push(item.link);
                }
                else
                {
                    links.push('');
                }
            }
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
        maintainAspectRatio: true,
        onHover: function(e) {
            var activeElement = barChart.getElementAtEvent(e);
            var cursor = 'default';
            if(activeElement.length >= 1)
            {
                var ix = activeElement[0]._index;
                var link = links[ix];
                if(link.length > 0) { cursor = 'pointer'; }
            }
            document.body.style.cursor = cursor;
        },
        onClick: function(e) {
            document.body.style.cursor = 'default';
            var activeElement = barChart.getElementAtEvent(e);
            if(activeElement.length >= 1)
            {
                var ix = activeElement[0]._index;
                var link = links[ix];
                if(link.length > 0) { window.location = link; }
            }
        }
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

function tagsScreen()
{
    $(".content-wrapper").load("./tags.html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }
    });
}

function tagScreen(id)
{
    $(".content-wrapper").load("./tags/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }
	$('.tag-add-rule').on('click', function()
	{
		var csrf = $('input[name="csrfmiddlewaretoken"]').val();

		var form = document.createElement('form');
		var i = document.createElement('input');
		var ci = document.createElement('input');
		form.method = "POST";
		form.action = "tagrules/" + id + ".html";
		i.name = "create";
		i.value = "rule";
		ci.name = "csrfmiddlewaretoken";
		ci.value = csrf;
		form.appendChild(i);
		form.appendChild(ci);
		document.body.appendChild(form);
		form.submit();

		return false;
	});
    });
}

function tagRulesScreen(id)
{
    $(".content-wrapper").load("./tagrules/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }
	$('.add-autotag-condition').on('click', function()
	{
		var ruleid = $(this).data('rule-id');
		var type = $("#condition-type-select-" + ruleid).val();
		$(".ruleid-field").val(ruleid);
		if(type == 'type') { $('#create-condition-type').modal('show'); }
		if(type == 'workout') { $('#create-condition-workout').modal('show'); }
		if(type == 'location') {
			$('#create-condition-location').modal('show');
		        //makeMap();

			var lat = {{ home.lat }};
			var lon = {{ home.lon }};
			$('#condition-lat').val(lat);
			$('#condition-lon').val(lon);
		        var map = L.map('mapselect', {center: [lat, lon], zoom: 13});
		        L.tileLayer('{{ tiles }}', {
		            attribution: 'Map data &copy; <a href="http://www.openstreetmap.org/">OpenStreetMap</a> contributors <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
		            maxZoom: 16
		        }).addTo(map);
		        map.on('click', function(e){
			    var RES = 100000;
			    var lat = Math.round(e.latlng.lat * RES) / RES;
			    var lon = Math.round(e.latlng.lng * RES) / RES;
			    $('#condition-lat').val(lat);
			    $('#condition-lon').val(lon);
			});

		        // The following block is required because we've foolishly put a leaflet map in a tab in a modal.
		        $("#create-condition-location").on('shown.bs.modal', function() 
		        {
		            map.invalidateSize();
		        });
		}
		return false;
	});
	$('.create-condition-button').on('click', function()
	{
		var formid = $(this).data('form');
		$('#' + formid).submit();
	});
	$('.tag-delete-tag').on('click', function()
	{
		$('#delete-tag').modal('show');

		return false;
	});
	$('.delete-autotag').on('click', function()
	{
		var ruleid = $(this).data('id');
		$(".ruleid-field").val(ruleid);
		$('#delete-autotag').modal('show');

		return false;
	});
	$('.delete-autotag-condition').on('click', function()
	{
		var ruleid = $(this).data('ruleid');
		var condid = $(this).data('condid');
		$(".ruleid-field").val(ruleid);
		$(".conditionid-field").val(condid);
		$('#delete-condition').modal('show');

		return false;
	});
	$('.delete-tag-button').on('click', function()
	{
		var formid = $(this).data('form');
		$('#' + formid).submit();
	});
	$('.delete-autotag-button').on('click', function()
	{
		var formid = $(this).data('form');
		$('#' + formid).submit();
	});
	$('.delete-condition-button').on('click', function()
	{
		var formid = $(this).data('form');
		$('#' + formid).submit();
	});
	$('.tag-add-rule').on('click', function()
	{
		var csrf = $('input[name="csrfmiddlewaretoken"]').val();

		var form = document.createElement('form');
		var i = document.createElement('input');
		var ci = document.createElement('input');
		form.method = "POST";
		form.action = "tagrules/" + id + ".html";
		i.name = "create";
		i.value = "rule";
		ci.name = "csrfmiddlewaretoken";
		ci.value = csrf;
		form.appendChild(i);
		form.appendChild(ci);
		document.body.appendChild(form);
		form.submit();

		return false;
	});

    });
}

function workoutScreen(id)
{
    $(".content-wrapper").load("./workout/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }
    });
}

function watchedDirectoryScreen(id)
{
    $(".content-wrapper").load("./watched_directory/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }

    });
}

function eventScreen(id)
{
    $(".content-wrapper").load("./events/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }

        makeMap();
        initialiseGraphics();
        $("#event-split-button").on('click', function()
        {
            $("form#event-split").submit();
            return false;
        });
        $("#event-save-form-button").on('click', function()
        {
            var data = [];
            $('.person_delete').each(function() {
                data.push($(this).data('id'));
            });
            var html = '<input type="hidden" id="people" name="people" value="' + data.join('|') + '"/>';
            $("form#event-edit").append(html);
            $("form#event-edit").submit();
            return false;
        });
	$("#person_add_submit").on('click', function()
	{
		var id = $('#person_add').val();
		var label = $('#person_add').find("option[value='" + id + "']").text();
		var html = '<div class="person_delete list-group-item" data-id="' + id + '">';
		html = html + '<img style="margin-right: 1em;" width="32" height="32" src="people/' + id + '_thumb.jpg"/>';
		html = html + label + ' ';
		html = html + '<small class="pull-right"><a class="delete_person btn btn-danger btn-sm" href="#" data-id="' + id + '">Delete</a></small>'
		html = html + '</div>';
		$('#event_people_list').append(html);
		$('.delete_person').off('click');
		$('.delete_person').on('click', function() { return eventPeopleDeleteName($(this).data('id')); });
	});
	$('.delete_person').on('click', function() { return eventPeopleDeleteName($(this).data('id')); });
        $("#event-delete-button").on('click', function(){ $("#event-event-delete").submit(); });
	activateImageEditor();
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

function importrdf(uri, callback)
{
            var url = './import-web.json';
            var data = {'url': uri};
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

    clearTimers();

    $("#imouto-search-text").on('keydown', function() { $("#imouto-search-results").html(''); });
    $("#imouto-search-text").on('keyup', typingDelay(function()
    {
        var text = $(this).val();
        var spinner = '<ul class="control-sidebar-menu"><li><span class="imitation-search-item"><i class="menu-icon fa fa-spinner fa-spin"></i><div class="menu-info"><h4 class="control-sidebar-subheading">Searching...</h4></div></span></li></ul>';
        if(text == '') { return; }
        $('#imouto-search-results').html(spinner);
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
            if(html.length == 0) { html = '<li><span class="imitation-search-item"><div class="menu-info"><h4 class="control-sidebar-subheading">No results</h4><p>Try broadening your search.</p></div></span></li>'; }
            $("#imouto-search-results").html('<ul class="control-sidebar-menu">' + html + '</ul>');
        });
    }, 500));
    $(".content-wrapper").html(loading);
    $(".control-sidebar").removeClass('control-sidebar-open');

    if(page == '') { homeScreen(); return true; }
    if(page == 'timeline') { timelineScreen(); return true; }
    if(page == 'files') { uploadScreen(); return true; }
    if(page == 'questionnaires') { questionIndexScreen(); return true; }
    if(page == 'import-web') { importWebScreen(); return true; }
    if(page == 'reports') { reportsScreen(); return true; }
    if(page == 'onthisday') { anniversaryScreen(); return true; }
    if(page == 'life-grid') { lifeGridScreen(); return true; }

    if(page == 'events') { eventsScreen(); return true; }
    if(page == 'people') { peopleScreen(); return true; }
    if(page == 'places') { placesScreen(); return true; }
    if(page == 'tags') { tagsScreen(); return true; }

    if(page.startsWith('day_')) { dayScreen(page.replace('day_', '')); }
    if(page.startsWith('month_')) { monthScreen(page.replace('month_', '')); }
    if(page.startsWith('year_')) { yearScreen(page.replace('year_', '')); }
    if(page.startsWith('tag_')) { tagScreen(page.replace('tag_', '')); }
    if(page.startsWith('tagrules_')) { tagRulesScreen(page.replace('tagrules_', '')); }
    if(page.startsWith('event_')) { eventScreen(page.replace('event_', '')); }
    if(page.startsWith('place_')) { placeScreen(page.replace('place_', '')); }
    if(page.startsWith('placecategory_')) { placeCategoryScreen(page.replace('placecategory_', '')); }
    if(page.startsWith('city_')) { cityScreen(page.replace('city_', '')); }
    if(page.startsWith('country_')) { countryScreen(page.replace('country_', '')); }
    if(page.startsWith('person_')) { personScreen(page.replace('person_', '')); }
    if(page.startsWith('workout_')) { workoutScreen(page.replace('workout_', '')); }
    if(page.startsWith('report_')) { var parse = page.replace('report_', '').split('_'); reportScreen(parse[0], parse[1]); }
    if(page.startsWith('watched_directory_')) { watchedDirectoryScreen(page.replace('watched_directory_', '')); }
    if(page.startsWith('questionnaire_')) { var parse = page.replace('questionnaire_', '').split('_'); questionEditScreen(parse[0], parse[1]); }

    if(page.startsWith('health-')) { healthReportScreen(page.replace('health-', '')); }

    if(page.startsWith('events_'))
    {
        var ds = page.replace('events_', '');
        $(".content-wrapper").load("./dayevents/" + ds + ".html", function(response, status, xhr){ if(status == 'error') { errorPage(xhr); return false; } });
    }
}

$(document).ready(function()
{
    $(".mood-select").on('click', function() {
        var m = $(this).data('mood');
        var url = "mood";
        var data = {'mood': m}
        $.ajax({
            url: url,
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify(data),
            method: 'POST',
            success: function(data) { console.log(data); }
        });
    });
    $(window).bind('hashchange', function(e) { pageRefresh(); });
    pageRefresh();
});
