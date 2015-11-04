describe("patch_strip_series_marker()", function() {
    var fn = pw.patch_strip_series_marker;

    it("should strip series markers", function() {
        res = fn("[1/2] foo");
        expect(res.order).toBe("1");
        expect(res.name).toBe("foo");
    });

    it("infer order when there's no series markers", function() {
        res = fn("foo");
        expect(res.order).toBe("1");
        expect(res.name).toBe("foo");

        res = fn("[i-g-t] foo");
        expect(res.order).toBe("1");
        expect(res.name).toBe("[i-g-t] foo");
    });

    it("strip only series markers", function() {
        res = fn("[v2,2/3] foo");
        expect(res.order).toBe("2");
        expect(res.name).toBe("[v2] foo");
    });

    it("don't fail if the series name contains '[' or ']'", function() {
        res = fn("[2/3] f[o]o");
        expect(res.order).toBe("2");
        expect(res.name).toBe("f[o]o");

        res = fn("f[o]o");
        expect(res.order).toBe("1");
        expect(res.name).toBe("f[o]o");

        /* That's really pushing it, but we never know */
        res = fn("f[2/3]o");
        expect(res.order).toBe("1");
        expect(res.name).toBe("f[2/3]o");
    });
});
