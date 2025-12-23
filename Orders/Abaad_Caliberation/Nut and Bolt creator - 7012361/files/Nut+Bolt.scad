/*
    Grandpa's nut and bolt generator
*/

use </root/snap/openscad/383/.local/share/OpenSCAD/threads.scad>

// ---- Parameters ----
bolt_diameter = 8;      // M8
thread_pitch = 1.25;
bolt_length = 40;
nut_height = 6.5;
head_height = 5.3;
head_width = 13;
clearance = 0.81;
show_bolt = true;
show_nut = true;

$fn = 100;

// ---- Modules ----

// Hex head
module hex_head(width, height) {
    cylinder(h=height, r=width / sqrt(3), $fn=6);
}

// Bolt body with threads
module bolt(d, pitch, length) {
    union() {
        // Bolt head
        hex_head(head_width, head_height);

        // Threaded shaft
        translate([0, 0, head_height])
            metric_thread(diameter=d, pitch=pitch, length=length, internal=false);
    }
}

// Nut with vertical thread axis, flat on bed
module nut(d, pitch, height) {
    difference() {
        // Outer hex shape
        hex_head(head_width, height);

        // Internal thread with clearance
        // Add 0.80mm for clearance
        metric_thread(diameter=d + clearance, pitch=pitch, length=height, internal=true);
    }
}

// ---- Render ----

if (show_bolt)
  // Bolt upright
  bolt(bolt_diameter, thread_pitch, bolt_length);

if (show_nut)
  // Nut laid flat, thread axis vertical, next to bolt
  translate([head_width * 2, 0, 0])
      nut(bolt_diameter, thread_pitch, nut_height);
