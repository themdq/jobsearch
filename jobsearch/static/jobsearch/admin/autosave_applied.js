document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.autosave-applied').forEach(function (cb) {
        cb.addEventListener('change', function () {
            const pk = this.dataset.id;
            const value = this.checked ? '1' : '0';
            const csrf = document.cookie.match(/csrftoken=([^;]+)/)[1];
            fetch('toggle-applied/' + pk + '/', {
                method: 'POST',
                headers: {'X-CSRFToken': csrf, 'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'value=' + value
            });
        });
    });
});
