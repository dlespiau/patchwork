$(function () {
    series_table = pw.setup_series_list('#serieslist');

    /* date filter */
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

    /* submitter filter */
    submitter_filter = pw.create_filter({
        table: series_table,
        name: 'submitter',
        init: function() {
            var _this = this;

            this.me = $('#submitter-me');
            this.by = $('#submitter-by');
            this.clear_filter(series_table);
            /* don't show the "submitted by me" option if there is no logged
             * in user */
            if (!pw.user.is_authenticated)
                this.me.attr('disabled', '');

            this.completion = pw.setup_autocompletion('#submitter-search',
                                                      '/submitter');
            this.completion.on('change', function() {
                _this.refresh_apply();
            });
        },
        set_filter: function(table) {
            var filter = null;
            var submitter = this.completion.getValue();

            if (this.me.prop('checked'))
                filter = 'self';
            else if (this.by.prop('checked') && submitter)
                filter = submitter;

            table.set_filter('submitter', filter);
        },
        clear_filter: function(table) {
            this.me.prop('checked', false);
            this.by.prop('checked', true);
            table.set_filter('submitter', null);
        },
        can_submit: function() {
            return this.me.prop('checked') ||
                   (this.by.prop('checked') && this.completion.getValue());
        },
        humanize: function() {
            if (this.me.prop('checked'))
                return 'submitted by me';
            var submitter = this.completion.getValue();
            return 'submitted by ' + this.completion.getItem(submitter).text();
        },
    });

    $('#submitter-filter input:radio').change(function() {
        submitter_filter.refresh_apply();
    });

    /* reviewer action */
    var reviewer_action = pw.create_action({
        table: series_table,
        name: 'reviewer',
        init: function() {
            var _this = this;

            this.me = $('#set-reviewer-me');
            this.to = $('#set-reviewer-to');

            /* don't allow the "assign to me" option if there is no logged in
             * user */
            if (!pw.user.is_authenticated)
                this.me.attr('disabled', '');

            this.completion = pw.setup_autocompletion('#set-reviewer-search',
                                                      '/complete_user');
            this.completion.on('change', function() {
                _this.refresh_apply();
            });
        },
        do_action: function(id) {
            var reviewer = null;

            if (this.me.prop('checked'))
                reviewer = pw.user.pk;
            else
                reviewer = this.completion.getValue();

            this.post_data('/series/' + id + '/', { reviewer: reviewer });
        },
        clear_action: function() {
            this.me.prop('checked', false);
            this.to.prop('checked', true);
            this.completion.clearOptions();
            this.completion.clear();
        },
        can_submit: function() {
            return this.me.prop('checked') ||
                   (this.to.prop('checked') && this.completion.getValue());
        },

    });

    $('#reviewer-action input:radio').change(function() {
        reviewer_action.refresh_apply();
    });
});
