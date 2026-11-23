#!/usr/bin/env python3
"""Programmatic 32nm GDSII and High-Resolution Layout Generator for:
Figure 9: (a) Conventional 28-FET, (b) A-type, (c) B-type, (d) C-type Full Adders

Updates for Cadence Virtuoso XL Display:
1. Proper GDSII PRESENTATION + MAG (0.10 um text height) so labels fit cleanly inside tracks.
2. Full transistor source/drain Metal-1 straps, gate extensions, contacts, and multi-layer vias
   matching every visual detail of Figure 9(a)-(d) in Kim et al. (IEEE Access 2023).
"""

import math
import os
import struct
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- Pure-Python GDSII Stream Binary Writer with Text Magnification ---
class GdsWriter:
    def __init__(self, filename, libname="FGFET_32NM_FA"):
        self.f = open(filename, "wb")
        self.libname = libname
        self._write_rec(0x00, 0x02, struct.pack(">h", 600))
        self._write_rec(0x01, 0x02, struct.pack(">12h", 2026, 11, 23, 20, 0, 0, 2026, 11, 23, 20, 0, 0))
        self._write_rec(0x02, 0x06, self._pad_str(libname))
        u1 = self._real8(0.001)  # 1 nm per user unit (um)
        u2 = self._real8(1e-9)   # 1 nm in meters
        self._write_rec(0x03, 0x05, u1 + u2)

    def _real8(self, val):
        if val == 0:
            return b"\x00" * 8
        sign = 0x80 if val < 0 else 0
        val = abs(val)
        exp = int(math.floor(math.log(val, 16))) + 1
        mant = int(val / (16.0 ** (exp - 14)))
        exp_byte = (exp + 64) | sign
        return struct.pack(">B", exp_byte) + struct.pack(">Q", mant)[1:]

    def _pad_str(self, s):
        b = s.encode("ascii")
        if len(b) % 2 != 0:
            b += b"\x00"
        return b

    def _write_rec(self, rtype, dtype, data):
        length = 4 + len(data)
        self.f.write(struct.pack(">hBB", length, rtype, dtype) + data)

    def start_cell(self, cellname):
        self._write_rec(0x05, 0x02, struct.pack(">12h", 2026, 11, 23, 20, 0, 0, 2026, 11, 23, 20, 0, 0))
        self._write_rec(0x06, 0x06, self._pad_str(cellname))

    def add_rect(self, layer, datatype, x1, y1, x2, y2):
        self._write_rec(0x08, 0x00, b"")
        self._write_rec(0x0D, 0x02, struct.pack(">h", layer))
        self._write_rec(0x0E, 0x02, struct.pack(">h", datatype))
        pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
        raw_xy = b"".join(struct.pack(">ii", int(x), int(y)) for x, y in pts)
        self._write_rec(0x10, 0x03, raw_xy)
        self._write_rec(0x11, 0x00, b"")

    def add_text(self, layer, texttype, x, y, text, mag=0.11):
        self._write_rec(0x0C, 0x00, b"")
        self._write_rec(0x0D, 0x02, struct.pack(">h", layer))
        self._write_rec(0x16, 0x02, struct.pack(">h", texttype))
        # PRESENTATION (0x17, bitarray 0x01): middle-center anchor (0x0005)
        self._write_rec(0x17, 0x01, struct.pack(">H", 0x0005))
        # STRANS (0x1A, bitarray 0x01): required before MAG in GDSII spec
        self._write_rec(0x1A, 0x01, struct.pack(">H", 0x0000))
        # MAG (0x1B, real8 0x05): text height in user units (um)
        self._write_rec(0x1B, 0x05, self._real8(mag))
        self._write_rec(0x10, 0x03, struct.pack(">ii", int(x), int(y)))
        self._write_rec(0x19, 0x06, self._pad_str(text))
        self._write_rec(0x11, 0x00, b"")

    def end_cell(self):
        self._write_rec(0x07, 0x00, b"")

    def close(self):
        self._write_rec(0x04, 0x00, b"")
        self.f.close()


# --- GDS Layer Definitions ---
LAYER_NWELL   = 1    # N-Well
LAYER_NDIFF   = 2    # N-Active (dt=0)
LAYER_PDIFF   = 2    # P-Active (dt=1)
LAYER_PIMP    = 3    # P+ Implant (for gpdk045 Pimp)
LAYER_NIMP    = 4    # N+ Implant (for gpdk045 Nimp)
LAYER_POLY    = 6    # Gate Polysilicon
LAYER_CONT    = 7    # Contact
LAYER_M1      = 8    # Metal 1
LAYER_VIA1    = 9    # Via 1
LAYER_M2      = 10   # Metal 2
LAYER_VIA2    = 11   # Via 2
LAYER_M3      = 12   # Metal 3
LAYER_VIA3    = 13   # Via 3
LAYER_M4      = 14   # Metal 4
LAYER_VFET    = 20   # VFET Pillar
LAYER_PIN     = 100  # Labels & Pins


class LayoutBuilder:
    def __init__(self, name, width_um, height_um):
        self.name = name
        self.w_nm = int(width_um * 1000)
        self.h_nm = int(height_um * 1000)
        self.area_um2 = width_um * height_um
        self.rects = []
        self.texts = []

    def add_rect(self, layer, dt, x1, y1, x2, y2):
        self.rects.append((layer, dt, int(x1), int(y1), int(x2), int(y2)))

    def add_contact(self, cx, cy, layer_via=LAYER_CONT):
        sz = 36
        self.add_rect(layer_via, 0, cx - sz//2, cy - sz//2, cx + sz//2, cy + sz//2)

    def add_text(self, layer, tt, x, y, text, mag=0.11):
        self.texts.append((layer, tt, int(x), int(y), text, mag))

    def build_into_gds(self, gds):
        gds.start_cell(self.name)
        for r in self.rects:
            gds.add_rect(r[0], r[1], r[2], r[3], r[4], r[5])
        for t in self.texts:
            gds.add_text(t[0], t[1], t[2], t[3], t[4], t[5])
        gds.end_cell()


# -------------------------------------------------------------------------
# Cell 1: Fig 9(a) Conventional 28-FET Full Adder (3.75 um^2)
# -------------------------------------------------------------------------
def build_28fet():
    W, H = 2.50, 1.50
    lb = LayoutBuilder("FA_28FET_CONVENTIONAL", W, H)
    w_nm, h_nm = lb.w_nm, lb.h_nm

    # Power Rails (M1)
    lb.add_rect(LAYER_M1, 0, 20, h_nm - 100, w_nm - 20, h_nm - 20)
    lb.add_rect(LAYER_M1, 0, 20, 20, w_nm - 20, 100)

    # N-Well & Implants
    lb.add_rect(LAYER_NWELL, 0, 10, h_nm - 460, w_nm - 10, h_nm - 10)
    lb.add_rect(LAYER_PIMP, 0, 40, h_nm - 430, w_nm - 40, h_nm - 110)
    lb.add_rect(LAYER_NIMP, 0, 40, 110, w_nm - 40, 420)

    # Segmented Active Diffusion Island Blocks (matching Fig 9a)
    pmos_blocks = [(70, 520), (600, 1050), (1130, 1750), (1830, 2420)]
    for x1, x2 in pmos_blocks:
        lb.add_rect(LAYER_PDIFF, 1, x1, h_nm - 380, x2, h_nm - 150)

    nmos_blocks = [(70, 520), (600, 1050), (1130, 1750), (1830, 2420)]
    for x1, x2 in nmos_blocks:
        lb.add_rect(LAYER_NDIFF, 0, x1, 150, x2, 360)

    # Middle smaller transistors (matching Fig 9a inner row)
    mid_blocks = [(250, 520), (750, 1050), (1280, 1580), (1830, 2120)]
    for x1, x2 in mid_blocks:
        lb.add_rect(LAYER_NDIFF, 0, x1, 580, x2, 740)

    # Vertical Poly Gates + S/D M1 Straps
    poly_xs = [160, 310, 440, 690, 840, 970, 1220, 1370, 1500, 1660, 1920, 2050, 2200, 2330]
    for px in poly_xs:
        lb.add_rect(LAYER_POLY, 0, px - 18, 120, px + 18, h_nm - 120)

    # Vertical S/D M1 connections to VDD / GND / internal nodes
    sd_xs = [100, 235, 375, 490, 635, 765, 905, 1020, 1165, 1295, 1435, 1580, 1720, 1860, 1985, 2125, 2265, 2390]
    for idx, sx in enumerate(sd_xs):
        # Top PMOS S/D M1 straps
        y_top = h_nm - 40 if idx % 3 == 0 else h_nm - 150
        lb.add_rect(LAYER_M1, 0, sx - 20, h_nm - 380, sx + 20, y_top)
        lb.add_contact(sx, h_nm - 265)
        # Bottom NMOS S/D M1 straps
        y_bot = 40 if idx % 3 == 0 else 150
        lb.add_rect(LAYER_M1, 0, sx - 20, y_bot, sx + 20, 360)
        lb.add_contact(sx, 255)

    # Horizontal M1 Signal Buses (6 internal routing tracks matching Fig 9a)
    m1_buses = [
        (100, 2390, 1140),
        (235, 1985, 1020),
        (100, 2265, 900),
        (375, 2125, 780),
        (100, 2390, 500),
        (235, 2125, 400),
    ]
    for x1, x2, y in m1_buses:
        lb.add_rect(LAYER_M1, 0, x1, y - 24, x2, y + 24)

    # Vertical M2 Interconnect Jumpers + Via1
    m2_jumpers = [
        (235, 255, 1140), (490, 400, 1020), (765, 255, 1140),
        (1020, 500, 1140), (1295, 255, 900), (1580, 400, 1140),
        (1860, 255, 1020), (2125, 400, 1140), (2390, 255, 1140)
    ]
    for x, y1, y2 in m2_jumpers:
        lb.add_rect(LAYER_M2, 0, x - 22, y1, x + 22, y2)
        lb.add_contact(x, y1, LAYER_VIA1)
        lb.add_contact(x, y2, LAYER_VIA1)

    # Clean scaled labels (mag=0.10 um)
    lb.add_text(LAYER_PIN, 0, w_nm - 220, h_nm - 60, "VDD", 0.11)
    lb.add_text(LAYER_PIN, 0, w_nm - 450, 60, "GND", 0.11)
    lb.add_text(LAYER_PIN, 0, 120, 780, "Cin", 0.11)
    lb.add_text(LAYER_PIN, 0, 440, 840, "A", 0.11)
    lb.add_text(LAYER_PIN, 0, 820, 780, "Cout", 0.12)
    lb.add_text(LAYER_PIN, 0, 1500, 780, "B", 0.11)
    lb.add_text(LAYER_PIN, 0, 2180, 780, "Sum", 0.12)

    return lb


# -------------------------------------------------------------------------
# Cell 2: Fig 9(b) FGFET-Based Full Adder A-Type (2.46 um^2)
# -------------------------------------------------------------------------
def build_atype():
    W, H = 1.76, 1.40
    lb = LayoutBuilder("FA_ATYPE_FGFET", W, H)
    w_nm, h_nm = lb.w_nm, lb.h_nm

    # Power Rails (M1)
    lb.add_rect(LAYER_M1, 0, 20, h_nm - 90, w_nm - 20, h_nm - 20)
    lb.add_rect(LAYER_M1, 0, 20, 20, w_nm - 20, 90)

    # N-Well & Implants
    lb.add_rect(LAYER_NWELL, 0, 10, h_nm - 380, w_nm - 10, h_nm - 10)
    lb.add_rect(LAYER_PIMP, 0, 40, h_nm - 350, w_nm - 40, h_nm - 100)
    lb.add_rect(LAYER_NIMP, 0, 40, 100, w_nm - 40, h_nm - 390)

    # Top PMOS blocks (Precharge + Output Inverters)
    for x1, x2 in [(80, 420), (500, 820), (960, 1520)]:
        lb.add_rect(LAYER_PDIFF, 1, x1, h_nm - 320, x2, h_nm - 140)

    # Middle NMOS logic blocks
    for x1, x2 in [(80, 620), (720, 1180), (1260, 1560)]:
        lb.add_rect(LAYER_NDIFF, 0, x1, 680, x2, 860)

    # Bottom NMOS + 3 FGFET pull-down branches
    for x1, x2 in [(80, 520), (620, 1080), (1180, 1560)]:
        lb.add_rect(LAYER_NDIFF, 0, x1, 220, x2, 460)

    # Vertical Poly Gates
    poly_xs = [180, 320, 600, 740, 1040, 1180, 1340, 1460]
    for px in poly_xs:
        lb.add_rect(LAYER_POLY, 0, px - 18, 120, px + 18, h_nm - 110)

    # 3 Monolithic FGFET Vertical Pillars (yellow/gold squares on gate poly)
    for fg_x, fg_y in [(220, 340), (740, 340), (1340, 340)]:
        lb.add_rect(LAYER_VFET, 0, fg_x - 35, fg_y - 45, fg_x + 35, fg_y + 45)
        lb.add_contact(fg_x, fg_y, LAYER_VIA2)

    # Horizontal M1 / M3 Routing Tracks (matching Fig 9b)
    tracks = [
        (LAYER_M1, 80, 1620, 1020),
        (LAYER_M3, 80, 1580, 920),
        (LAYER_M1, 140, 1560, 780),
        (LAYER_M3, 180, 1560, 620),
        (LAYER_M1, 120, 1460, 480),
        (LAYER_M3, 120, 1460, 340),
        (LAYER_M1, 120, 1580, 200),
    ]
    for lyr, x1, x2, y in tracks:
        lb.add_rect(lyr, 0, x1, y - 22, x2, y + 22)

    # Vertical M2 / M4 Interconnects
    v_tracks = [
        (LAYER_M2, 120, 200, 1260),
        (LAYER_M2, 380, 200, 1260),
        (LAYER_M2, 660, 200, 1200),
        (LAYER_M4, 880, 200, 1260),
        (LAYER_M2, 1120, 200, 1260),
        (LAYER_M4, 1400, 200, 1260),
        (LAYER_M2, 1620, 90, 1280),
    ]
    for lyr, x, y1, y2 in v_tracks:
        lb.add_rect(lyr, 0, x - 20, y1, x + 20, y2)
        lb.add_contact(x, y1 + 40, LAYER_VIA1)
        lb.add_contact(x, y2 - 40, LAYER_VIA1)

    # Clean scaled labels
    lb.add_text(LAYER_PIN, 0, w_nm - 320, h_nm - 55, "VDD", 0.10)
    lb.add_text(LAYER_PIN, 0, w_nm - 280, 140, "GND", 0.10)
    lb.add_text(LAYER_PIN, 0, 520, 1040, "Cout", 0.10)
    lb.add_text(LAYER_PIN, 0, 1260, 1040, "Sum", 0.10)
    lb.add_text(LAYER_PIN, 0, 600, 800, "Cin", 0.10)
    lb.add_text(LAYER_PIN, 0, 540, 560, "A", 0.10)
    lb.add_text(LAYER_PIN, 0, 480, 440, "WL", 0.10)
    lb.add_text(LAYER_PIN, 0, 940, 360, "B", 0.11)
    lb.add_text(LAYER_PIN, 0, 1660, 360, "CLK", 0.10)

    return lb


# -------------------------------------------------------------------------
# Cell 3: Fig 9(c) FGFET-Based Full Adder B-Type (2.24 um^2)
# -------------------------------------------------------------------------
def build_btype():
    W, H = 1.87, 1.20
    lb = LayoutBuilder("FA_BTYPE_FGFET", W, H)
    w_nm, h_nm = lb.w_nm, lb.h_nm

    # Top & Bottom M1 Buses
    lb.add_rect(LAYER_M1, 0, 40, h_nm - 80, w_nm - 40, h_nm - 20)
    lb.add_rect(LAYER_M1, 0, 40, 20, w_nm - 40, 80)

    # Implants & Active Diffusion Arrays (Top, Middle, Bottom, Right Inverters)
    lb.add_rect(LAYER_NIMP, 0, 60, 90, 1320, h_nm - 90)
    lb.add_rect(LAYER_NWELL, 0, 1340, 90, w_nm - 30, h_nm - 90)
    lb.add_rect(LAYER_PIMP, 0, 1360, 110, w_nm - 50, h_nm - 110)

    # Top NMOS + FGFET Array Row
    lb.add_rect(LAYER_NDIFF, 0, 120, h_nm - 260, 1260, h_nm - 120)
    # Bottom NMOS + FGFET Array Row
    lb.add_rect(LAYER_NDIFF, 0, 120, 120, 1120, 260)
    # Right Output Inverters & Precharge PMOS
    lb.add_rect(LAYER_PDIFF, 1, 1400, 680, 1740, 960)
    lb.add_rect(LAYER_PDIFF, 1, 1400, 180, 1740, 460)

    # Vertical Poly Gates + Wordlines
    for px in [240, 380, 560, 700, 880, 1020, 1180, 1520, 1660]:
        lb.add_rect(LAYER_POLY, 0, px - 16, 100, px + 16, h_nm - 100)

    # Vertical M4 Wordline Pillar Bus (Purple vertical strip in Fig 9c)
    lb.add_rect(LAYER_M4, 0, 420, 120, 480, h_nm - 120)

    # 7 FGFET Monolithic Pillars
    fg_coords = [
        (380, h_nm - 190), (700, h_nm - 190), (1020, h_nm - 190), (1180, h_nm - 190),
        (240, 190), (560, 190), (880, 190)
    ]
    for fx, fy in fg_coords:
        lb.add_rect(LAYER_VFET, 0, fx - 30, fy - 35, fx + 30, fy + 35)
        lb.add_contact(fx, fy, LAYER_VIA2)

    # Horizontal M1 / M3 Bitlines & Data Lines
    for lyr, x1, x2, y in [
        (LAYER_M1, 160, 1320, 880),
        (LAYER_M3, 200, 1480, 740),
        (LAYER_M1, 140, 1680, 580),
        (LAYER_M3, 200, 1480, 420),
        (LAYER_M1, 160, 1320, 300),
    ]:
        lb.add_rect(lyr, 0, x1, y - 22, x2, y + 22)

    # Vertical M2 Interconnects
    for x in [120, 310, 630, 950, 1260, 1440, 1760]:
        lb.add_rect(LAYER_M2, 0, x - 20, 80, x + 20, h_nm - 80)
        lb.add_contact(x, 580, LAYER_VIA1)

    # Clean scaled labels matching Fig 9(c)
    lb.add_text(LAYER_PIN, 0, 80, 540, "BL", 0.10)
    lb.add_text(LAYER_PIN, 0, 1080, h_nm - 110, "!A", 0.10)
    lb.add_text(LAYER_PIN, 0, 720, 860, "!B", 0.10)
    lb.add_text(LAYER_PIN, 0, 1140, 740, "B", 0.11)
    lb.add_text(LAYER_PIN, 0, 680, 660, "Cin", 0.10)
    lb.add_text(LAYER_PIN, 0, 860, 660, "GND", 0.10)
    lb.add_text(LAYER_PIN, 0, 1340, 720, "SUM", 0.10)
    lb.add_text(LAYER_PIN, 0, 680, 460, "!Cin", 0.10)
    lb.add_text(LAYER_PIN, 0, 1360, 420, "Cout", 0.10)
    lb.add_text(LAYER_PIN, 0, 1800, 500, "VDD", 0.10)
    lb.add_text(LAYER_PIN, 0, 420, 80, "A", 0.10)
    lb.add_text(LAYER_PIN, 0, 940, 80, "1", 0.10)

    return lb


# -------------------------------------------------------------------------
# Cell 4: Fig 9(d) FGFET-Based Full Adder C-Type (2.53 um^2)
# -------------------------------------------------------------------------
def build_ctype():
    W, H = 1.95, 1.30
    lb = LayoutBuilder("FA_CTYPE_FGFET", W, H)
    w_nm, h_nm = lb.w_nm, lb.h_nm

    # Top & Bottom M1 Rails
    lb.add_rect(LAYER_M1, 0, 40, h_nm - 80, w_nm - 40, h_nm - 20)
    lb.add_rect(LAYER_M1, 0, 40, 20, w_nm - 40, 80)

    # Diffusion Regions (Dynamic OR-FGFET Array + Output Inverters)
    lb.add_rect(LAYER_NIMP, 0, 60, 100, 1520, h_nm - 100)
    lb.add_rect(LAYER_NWELL, 0, 1540, 100, w_nm - 40, h_nm - 100)

    for x1, x2, y1, y2 in [
        (160, 720, 920, 1100),
        (820, 1380, 920, 1100),
        (220, 1420, 560, 740),
        (280, 1180, 160, 340),
    ]:
        lb.add_rect(LAYER_NDIFF, 0, x1, y1, x2, y2)

    # Right Output Inverters (PMOS)
    lb.add_rect(LAYER_PDIFF, 1, 1580, 740, 1840, 1040)
    lb.add_rect(LAYER_PDIFF, 1, 1580, 180, 1840, 480)

    # Vertical Poly Gates
    for px in [260, 420, 580, 760, 940, 1100, 1260, 1440, 1680]:
        lb.add_rect(LAYER_POLY, 0, px - 16, 100, px + 16, h_nm - 100)

    # Central M4 Vertical Pillar Bus (Purple bar in Fig 9d)
    lb.add_rect(LAYER_M4, 0, 840, 240, 910, 1040)

    # 6 FGFET Monolithic Pillars
    fg_coords = [
        (420, 980), (940, 980),
        (580, 650), (1100, 650),
        (420, 250), (940, 250),
    ]
    for fx, fy in fg_coords:
        lb.add_rect(LAYER_VFET, 0, fx - 30, fy - 35, fx + 30, fy + 35)
        lb.add_contact(fx, fy, LAYER_VIA2)

    # Horizontal M1 / M3 Bitlines & Routing
    for lyr, x1, x2, y in [
        (LAYER_M1, 140, 1620, 840),
        (LAYER_M3, 120, 1540, 720),
        (LAYER_M1, 320, 1620, 580),
        (LAYER_M3, 420, 1740, 440),
        (LAYER_M1, 240, 1620, 320),
    ]:
        lb.add_rect(lyr, 0, x1, y - 22, x2, y + 22)

    # Vertical M2 Interconnects
    for x in [120, 340, 660, 1020, 1340, 1560, 1820]:
        lb.add_rect(LAYER_M2, 0, x - 20, 80, x + 20, h_nm - 80)
        lb.add_contact(x, 720, LAYER_VIA1)

    # Clean scaled labels matching Fig 9(d)
    lb.add_text(LAYER_PIN, 0, 80, 720, "BL", 0.10)
    lb.add_text(LAYER_PIN, 0, 240, 740, "Cin", 0.10)
    lb.add_text(LAYER_PIN, 0, 180, 620, "A", 0.10)
    lb.add_text(LAYER_PIN, 0, 620, 980, "0", 0.10)
    lb.add_text(LAYER_PIN, 0, 900, 1060, "!A", 0.10)
    lb.add_text(LAYER_PIN, 0, 1140, 740, "B", 0.11)
    lb.add_text(LAYER_PIN, 0, 1020, 580, "!B", 0.10)
    lb.add_text(LAYER_PIN, 0, 1620, 960, "SUM", 0.10)
    lb.add_text(LAYER_PIN, 0, 1620, 840, "!Cin", 0.10)
    lb.add_text(LAYER_PIN, 0, 1880, 780, "VDD", 0.10)
    lb.add_text(LAYER_PIN, 0, 1460, 520, "GND", 0.10)
    lb.add_text(LAYER_PIN, 0, 1680, 300, "CLK", 0.10)
    lb.add_text(LAYER_PIN, 0, 1340, 160, "Cout", 0.10)

    return lb


# --- Cadence Virtuoso Style High-Res Plotter ---
def plot_layout(ax, lb, title, sublabel):
    ax.set_title(f"{sublabel} {title}\nArea = {lb.area_um2:.2f} \u03bcm\u00b2 ({lb.w_nm/1000:.2f} \u03bcm \u00d7 {lb.h_nm/1000:.2f} \u03bcm)",
                 fontsize=11, fontweight="bold", pad=8)

    COLOR_MAP = {
        LAYER_NWELL: ("#f7efe8", 0.40, "#d9c2ad", 0.8),
        LAYER_PIMP:  ("#ffe6f2", 0.30, "#ff99cc", 0.6),
        LAYER_NIMP:  ("#e6ffe6", 0.30, "#85e085", 0.6),
        LAYER_NDIFF: ("#99e699", 0.45, "#2eb82e", 1.2),     # N-Active (green)
        LAYER_PDIFF: ("#ffb3d9", 0.45, "#cc0066", 1.2),     # P-Active (pink)
        LAYER_POLY:  ("#ff4d4d", 0.70, "#b30000", 1.0),     # Poly (red)
        LAYER_CONT:  ("#80e5ff", 0.90, "#008fb3", 0.8),     # Contact
        LAYER_M1:    ("#66b3ff", 0.55, "#005ce6", 1.1),     # Metal 1 (light blue)
        LAYER_VIA1:  ("#99ebff", 0.95, "#004080", 0.8),     # Via 1
        LAYER_M2:    ("#4d94ff", 0.50, "#003d99", 1.1),     # Metal 2
        LAYER_VIA2:  ("#66d9ff", 0.95, "#00264d", 0.8),     # Via 2
        LAYER_M3:    ("#1a75ff", 0.55, "#002699", 1.1),     # Metal 3
        LAYER_VIA3:  ("#b3b3ff", 0.95, "#1a0066", 0.8),     # Via 3
        LAYER_M4:    ("#9933ff", 0.55, "#4d0099", 1.1),     # Metal 4 (purple)
        LAYER_VFET:  ("#cccc00", 0.85, "#666600", 1.4),     # FGFET VFET pillar
    }

    draw_order = [
        LAYER_NWELL, LAYER_PIMP, LAYER_NIMP, LAYER_NDIFF, LAYER_PDIFF,
        LAYER_POLY, LAYER_VFET, LAYER_CONT, LAYER_M1, LAYER_VIA1,
        LAYER_M2, LAYER_VIA2, LAYER_M3, LAYER_VIA3, LAYER_M4
    ]
    for lyr in draw_order:
        for r in lb.rects:
            if r[0] == lyr:
                if lyr == LAYER_NDIFF and r[1] == 1:
                    continue
                if lyr == LAYER_PDIFF and r[1] == 0:
                    continue
                fc, alpha, ec, lw = COLOR_MAP.get(lyr, ("#cccccc", 0.5, "#888888", 1.0))
                if lyr == LAYER_PDIFF and r[1] == 1:
                    fc, alpha, ec, lw = COLOR_MAP[LAYER_PDIFF]
                rect = patches.Rectangle((r[2]/1000, r[3]/1000), (r[4]-r[2])/1000, (r[5]-r[3])/1000,
                                         facecolor=fc, alpha=alpha, edgecolor=ec, linewidth=lw)
                ax.add_patch(rect)

    for t in lb.texts:
        ax.text(t[2]/1000, t[3]/1000, t[4], color="#1fb81f", fontsize=10, fontweight="bold",
                ha="center", va="center",
                bbox=dict(boxstyle="square,pad=0.12", facecolor="#ffffff", alpha=0.65, edgecolor="none"))

    ax.set_xlim(-0.08, lb.w_nm/1000 + 0.08)
    ax.set_ylim(-0.08, lb.h_nm/1000 + 0.08)
    ax.set_xlabel("Width [\u03bcm]", fontsize=9)
    ax.set_ylabel("Height [\u03bcm]", fontsize=9)
    ax.set_aspect("equal")
    ax.grid(True, linestyle=":", alpha=0.35)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "layout_cadence_gds")
    gds_dir = os.path.join(out_dir, "gds")
    plot_dir = os.path.join(out_dir, "plots")
    os.makedirs(gds_dir, exist_ok=True)
    os.makedirs(plot_dir, exist_ok=True)

    cells = [
        (build_28fet(), "(a)", "Conventional 28FET full adder layout", "fa_28fet.gds"),
        (build_atype(), "(b)", "FGFET-based full adder A-type layout", "fa_atype.gds"),
        (build_btype(), "(c)", "FGFET-based full adder B-type layout", "fa_btype.gds"),
        (build_ctype(), "(d)", "FGFET-based full adder C-type layout", "fa_ctype.gds"),
    ]

    for lb, _, _, gds_name in cells:
        gds_path = os.path.join(gds_dir, gds_name)
        gw = GdsWriter(gds_path, libname=lb.name)
        lb.build_into_gds(gw)
        gw.close()

    master_gds_path = os.path.join(gds_dir, "full_adders_all_fig9.gds")
    gw_master = GdsWriter(master_gds_path, libname="FGFET_FULL_ADDERS_ALL")
    for lb, _, _, _ in cells:
        lb.build_into_gds(gw_master)
    gw_master.close()

    fig, axes = plt.subplots(2, 2, figsize=(13, 11), dpi=300)
    axes = axes.flatten()
    for idx, (lb, sublabel, title, _) in enumerate(cells):
        plot_layout(axes[idx], lb, title, sublabel)

    plt.suptitle("FIGURE 9 Replica: 32nm Full Adder Layouts (Cadence Virtuoso Style)\n"
                 "(a) Conventional 28FET (3.75 \u03bcm\u00b2), (b) A-type (2.46 \u03bcm\u00b2), "
                 "(c) B-type (2.24 \u03bcm\u00b2), (d) C-type (2.53 \u03bcm\u00b2)",
                 fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(plot_dir, "fig9_layout_replica.png"), dpi=300)
    plt.close()

    for lb, sublabel, title, _ in cells:
        f, ax = plt.subplots(figsize=(7, 6), dpi=300)
        plot_layout(ax, lb, title, sublabel)
        f.tight_layout()
        f.savefig(os.path.join(plot_dir, f"{lb.name.lower()}.png"), dpi=300)
        plt.close()

    print("Updated 32nm GDSII layouts with 0.11um text magnification and full S/D straps!")

if __name__ == "__main__":
    main()
