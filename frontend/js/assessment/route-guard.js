(function () {
    try {
        var p = window.location.pathname || '';
        if (!p.startsWith('/assessment/')) return;
        var ua = (navigator.userAgent || '').toLowerCase();
        var isMobileUa = /android|iphone|ipad|ipod|mobile|windows phone|harmonyos/.test(ua);
        var isNarrow = window.matchMedia && window.matchMedia('(max-width: 768px)').matches;
        if (isMobileUa && isNarrow) {
            var target = '/m' + p + (window.location.search || '') + (window.location.hash || '');
            window.location.replace(target);
        }
    } catch (_) {}
})();

