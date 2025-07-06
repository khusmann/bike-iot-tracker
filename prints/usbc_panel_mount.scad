$fn = 50;
difference() {
    resize([13, 25]) cylinder(0.8, d=1);
    for (i = [-1, 1]) {
        translate([0, 8*i, 0]) cylinder(10, d = 3.2, center=true);
    }
    cylinder(10, d = 10, center=true);
}