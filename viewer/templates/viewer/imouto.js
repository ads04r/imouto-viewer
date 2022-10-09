var map;
var quiz;
var quiz_score_a;
var quiz_score_d;

function errorPage(e)
{
    console.log(e);

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

function uploadScreen()
{
    $(".content-wrapper").load("./upload.html", function(response, status, xhr){

        if(status == 'error') { errorPage(xhr); return false; }

	window.setInterval(updateUploadStats, 1000);
	window.setInterval(updateUploadQueue, 5000);
	updateUploadStats();
	updateUploadQueue();

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

				if(item.error) { icon = '<i class="fa fa-warning text-danger"></i>'; }
				if(item.running) { icon = '<i class="fa fa-play-circle text-success"></i>'; }
				if(item.event)
				{
					title = item.event.caption;
					type = item.event.type;
					url = '#event_' + item.event.id;
				}
				if(item.report)
				{
					title = item.report.label;
					type = item.report.year;
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
    var url = "process";

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

function onLocEventMapClick(e)
{
    var RES = 100000;
    var lat = Math.round(e.latlng.lat * RES) / RES;
    var lon = Math.round(e.latlng.lng * RES) / RES;
    var canvas = $('#location_event_select');
    var url = 'days/' + canvas.data('date') + '/locevents.json';
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
                html = html + '<td data-start="' + item.start_time + '" data-end="' + item.end_time + '">' + item.text + '</td>';
                html = html + '<td class="pull-right"><a data-start="' + item.start_time + '" data-end="' + item.end_time + '" class="btn btn-success btn-xs addlocationevent" href="#">Add Event</a></td>';
                html = html + '</tr>';
            }
            if(html == '')
            {
                html = '<p>No events found in this location.</p>';
            } else {
                html = '<div class="table-responsive"><table class="table no-margin">' + html + '</table></div>'
            }
            canvas.html(html);
            $('.addlocationevent').on('click', function() {
                var url = 'events.html';
                var form = new FormData();
                var dss = $(this).data('start');
                var dse = $(this).data('end');
                var caption = $(this).parent().parent().find('td:not(.pull-right)').text()
                form.append('type', 'loc_prox');
                form.append('csrfmiddlewaretoken', csrf);
                form.append('start_time', dss);
                form.append('end_time', dse);
                form.append('workout_type', '');
                form.append('caption', caption);
                form.append('location', '');
                form.append('description', '');
                $.ajax({
                    url: url,
                    processData: false,
                    contentType: false,
                    data: form,
                    method: 'POST',
                    success: function() { window.location.reload(false); }
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
	console.log(year);
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
	window.setInterval(updateReportQueue, 5000);
	updateReportQueue();
    });
}

function reportScreen(id)
{
    $(".content-wrapper").load("./reports/" + id + ".html", function(response, status, xhr){
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

function popQuestion()
{
	if(quiz.length == 0)
	{
                var data = {'anxiety': quiz_score_a, 'depression': quiz_score_d}
                $.ajax({
                    url: "health/mentalhealth.html",
                    dataType: 'json',
                    contentType: 'application/json',
                    data: JSON.stringify(data),
                    method: 'POST',
                    success: function() {
			window.location.reload(false);
		    }
                });
		return false;
	}

	var item = quiz.pop();

	$("#quiz-question").html(item[0]);
        $("#hads-question-type").val(item[1]);
	for (var i = 0; i < 4; i++)
	{
		$("#quiz-answer-" + i).html(item[2][i]);
		$("#hads-radio-" + i).val(item[3][i]);
		$("#hads-radio-" + i).removeAttr('checked');
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
			html = html + "<tr><td>Bed time:</td><td>" + data.bedtime_local + "</td></tr>";
			html = html + "<tr><td>Wake time:</td><td>" + Math.floor(data.length / (60 * 60)) + " hours</td></tr>";
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
            var dt = new Date();
            dt.setDate(dt.getDate() - 1);
            var dsy = String(dt.getFullYear());
            var dsm = String(dt.getMonth() + 1);
            var dsd = String(dt.getDate());
            var ds = dsy + dsm.padStart(2, '0') + dsd.padStart(2, '0');
            daySleepReport(ds);
            $(".sleep-area-chart").each(function() {
                var data = $(this).data('data');
                makeSleepAreaChart($(this), data);
            });
        }
        if(page == 'mentalhealth')
        {
            quiz = [
                ["I feel tense or 'wound up'", "A", ["most of the time", "a lot of the time", "from time to time, occasionally", "not at all"], [3, 2, 1, 0]],
                ["I feel as if I am slowed down", "D", ["nearly all the time", "very often", "sometimes", "not at all"], [3, 2, 1, 0]],
                ["I still enjoy the things I used to enjoy", "D", ["definitely as much", "not quite so much", "only a little", "hardly at all"], [0, 1, 2, 3]],
                ["I get a sort of frightened feeling like 'butterflies' in the stomach", "A", ["not at all", "occasionally", "quite often", "very often"], [0, 1, 2, 3]],
                ["I get a sort of frightened feeling as if something awful is about to happen", "A", ["very definitely and quite badly", "yes, but not too badly", "a little, but it doesn't worry me", "not at all"], [3, 2, 1, 0]],
                ["I have lost interest in my appearance", "D", ["definitely", "I don't take as much care as I should", "I may not take quite as much care", "I take just as much care as ever"], [3, 2, 1, 0]],
                ["I can laugh and see the funny side of things", "D", ["as much as I always could", "not quite so much now", "definitely not so much now", "not at all"], [0, 1, 2, 3]],
                ["I feel restless as if I have to be on the move", "A", ["very much indeed", "quite a lot", "not very much", "not at all"], [3, 2, 1, 0]],
                ["Worrying thoughts go through my mind", "A", ["a great deal of the time", "a lot of the time", "from time to time, but not too often", "only occasionally"], [3, 2, 1, 0]],
                ["I look forward with enjoyment to things", "D", ["as much as I ever did", "rather less than I used to", "definitely less than I used to", "hardly at all"], [0, 1, 2, 3]],
                ["I feel cheerful", "D", ["not at all", "not often", "sometimes", "most of the time"], [3, 2, 1, 0]],
                ["I get sudden feelings of panic", "A", ["very often indeed", "quite often", "not very often", "not at all"], [3, 2, 1, 0]],
                ["I can sit at ease and feel relaxed", "A", ["definitely", "usually", "not often", "not at all"], [0, 1, 2, 3]],
                ["I can enjoy a good book or radio or TV program", "D", ["often", "sometimes", "not often", "very seldom"], [0, 1, 2, 3]]
            ];
            array_shuffle(quiz);
            quiz_score_a = 0;
            quiz_score_d = 0;
            $("#data-next-button").on('click', function() {
                var value = $('input[name=hads-radio]:checked', 'form').val();
                var type = $("#hads-question-type").val();
                if(value === undefined) { alert("Select an answer before continuing."); return false; }
                if(type == 'A') { quiz_score_a = quiz_score_a + parseInt(value); }
                if(type == 'D') { quiz_score_d = quiz_score_d + parseInt(value); }
                popQuestion();
            });
            popQuestion();
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

        var lat = 50.9;
        var lon = -1.4;
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
			html = html + "<div class=\"box-body\">";

			html = html + "<p>Daily Heart Activity</p>";

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

		if((data.wake_up_local) && (data.sleep)){
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
			html = html + "</table>";
			$(".day-stats").html(html);
		}

		html = "";

		if(data.sleep){

			html = html + "<div class=\"box box-primary\">";
			html = html + "<div class=\"box-body\">";

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

			html = html + "</div>";
			html = html + "</div>";
		}

		if(html != '') { $(".day-sleep-summary").html(html); }
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
    $(".content-wrapper").load("./people.html", function(response, status, xhr){ if(status == 'error') { errorPage(xhr); return false; } });
}

function personScreen(id)
{
    $(".content-wrapper").load("./people/" + id + ".html", function(response, status, xhr){ if(status == 'error') { errorPage(xhr); return false; } });
}

function placesScreen(id)
{
    $(".content-wrapper").load("./places.html", function(response, status, xhr){

        if(status == 'error') { errorPage(xhr); return false; }

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
    $(".content-wrapper").load("./places/" + id + ".html", function(response, status, xhr){
        if(status == 'error') { errorPage(xhr); return false; }
        makeMap();
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

function makeDonutChart(donutChartCanvas, data, labels)
{
    var donutChart = new Chart(donutChartCanvas);
    var colours = ['#ABC1D8', '#3C8DBC', '#0073B7', '#005C92'];
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
            animation: { animateScale: true, animateRotate: true },
            legend: { display: false },
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
            maintainAspectRatio: true
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
    });
}

function eventScreen(id)
{
    $(".content-wrapper").load("./events/" + id + ".html", function(response, status, xhr)
    {
        if(status == 'error') { errorPage(xhr); return false; }

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
    if(page == 'tags') { tagsScreen(); return true; }
                                        
    if(page.startsWith('day_')) { dayScreen(page.replace('day_', '')); }
    if(page.startsWith('tag_')) { tagScreen(page.replace('tag_', '')); }
    if(page.startsWith('event_')) { eventScreen(page.replace('event_', '')); }
    if(page.startsWith('place_')) { placeScreen(page.replace('place_', '')); }
    if(page.startsWith('person_')) { personScreen(page.replace('person_', '')); }
    if(page.startsWith('report_')) { reportScreen(page.replace('report_', '')); }
                            
    if(page.startsWith('health-')) { healthReportScreen(page.replace('health-', '')); }

    if(page.startsWith('events_'))
    {
        var ds = page.replace('events_', '');
        $(".content-wrapper").load("./dayevents/" + ds + ".html", function(response, status, xhr){ if(status == 'error') { errorPage(xhr); return false; } });
    }
}

$(document).ready(function()
{
    $(window).bind('hashchange', function(e) { pageRefresh(); });
    pageRefresh();
});