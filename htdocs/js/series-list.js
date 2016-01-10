$(function () {
    series_table = pw.setup_series_list('#serieslist');

    date_filter = pw.create_filter({
        table: series_table,
        name: 'date',
        init: function() {
            $('.input-group.date').datepicker({
                clearBtn: true,
                todayHighlight: true,
                autoclose: true,
                format: 'yyyy-mm-dd',

            });
        },
        set_filter: function(table) {
            table.set_filter('updated_since', $('#date-from').val());
            table.set_filter('updated_before', $('#date-to').val());
        },
        clear_filter: function(table) {
            $('.input-group.date').datepicker('update', '');
            table.set_filter('updated_since', null);
            table.set_filter('updated_before', null);
        },
        can_submit: function() {
            return $('#date-from').val().trim() ||
                   $('#date-to').val().trim();
        },
        humanize: function() {
            var from = $('#date-from').val().trim(),
                to = $('#date-to').val().trim();

            if (from && to)
                return 'updated between ' + from + ' and ' + to;
            else if (from)
                return 'updated since ' + from;
            else if (to)
                return 'updated before ' + to;
            return null;
        },
    });

    $('.input-group.date').datepicker().on('changeDate', function(e) {
        date_filter.refresh_apply();
    });

});
