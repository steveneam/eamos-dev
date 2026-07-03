export interface GnomadMapAnchor {
  x: number
  y: number
  regionPath: string
  context: string
}

export const GNOMAD_ANCESTRY_MAP_VERSION = 'eamos-gnomad-ancestry-map-v4'

// Eamos proprietary visual anchor layer: gnomAD group labels describe
// source genetic-similarity cohorts, not patient ancestry or exact geography.
export const GNOMAD_ANCESTRY_MAP_ANCHORS: Record<string, GnomadMapAnchor> = {
  afr: {
    x: 1040,
    y: 510,
    regionPath:
      'M930 374 C992 345 1088 356 1152 398 C1214 441 1224 526 1190 622 C1152 728 1064 792 986 734 C928 691 898 610 902 518 C905 456 890 410 930 374 Z',
    context: 'gnomAD AFR: African / African American; oriented over Africa for map context',
  },
  ami: {
    x: 505,
    y: 300,
    regionPath:
      'M420 235 C504 186 640 199 706 270 C688 350 566 371 475 335 C410 310 382 270 420 235 Z',
    context: 'gnomAD AMI: Amish founder population; oriented over North America for map context',
  },
  amr: {
    x: 575,
    y: 500,
    regionPath:
      'M530 390 C612 360 700 400 735 480 C730 554 688 626 668 715 C646 798 590 790 565 706 C548 625 490 560 492 480 C495 435 510 405 530 390 Z',
    context: 'gnomAD AMR: Admixed American; oriented over the Americas for map context',
  },
  asj: {
    x: 1135,
    y: 285,
    regionPath:
      'M1088 245 C1125 220 1185 230 1220 270 C1200 318 1138 330 1090 305 C1060 285 1060 260 1088 245 Z',
    context:
      'gnomAD ASJ: Ashkenazi Jewish; diaspora group, oriented near Europe / Middle East for map context',
  },
  eas: {
    x: 1530,
    y: 315,
    regionPath:
      'M1450 230 C1535 185 1660 190 1730 275 C1735 360 1675 440 1575 450 C1482 425 1415 340 1450 230 Z',
    context: 'gnomAD EAS: East Asian; oriented over East Asia for map context',
  },
  fin: {
    x: 1105,
    y: 160,
    regionPath:
      'M1085 125 C1125 100 1165 115 1175 155 C1172 190 1145 215 1105 205 C1075 190 1065 150 1085 125 Z',
    context: 'gnomAD FIN: Finnish; oriented over Finland / northern Europe for map context',
  },
  mid: {
    x: 1270,
    y: 335,
    regionPath:
      'M1180 285 C1245 260 1320 275 1375 320 C1370 380 1295 420 1225 390 C1170 365 1150 320 1180 285 Z',
    context: 'gnomAD MID: Middle Eastern; oriented over the Middle East for map context',
  },
  nfe: {
    x: 1045,
    y: 235,
    regionPath:
      'M960 190 C1010 150 1105 150 1180 190 C1210 230 1190 285 1135 315 C1065 340 990 310 945 270 C920 235 930 205 960 190 Z',
    context: 'gnomAD NFE: European, non-Finnish; oriented over Europe for map context',
  },
  remaining: {
    x: 1010,
    y: 410,
    regionPath:
      'M955 350 C1030 320 1110 332 1165 385 C1140 448 1050 465 980 435 C935 415 920 375 955 350 Z',
    context: 'gnomAD RMI: Remaining individuals not assigned to current gnomAD labels',
  },
  rmi: {
    x: 1010,
    y: 410,
    regionPath:
      'M955 350 C1030 320 1110 332 1165 385 C1140 448 1050 465 980 435 C935 415 920 375 955 350 Z',
    context: 'gnomAD RMI: Remaining individuals not assigned to current gnomAD labels',
  },
  sas: {
    x: 1375,
    y: 400,
    regionPath:
      'M1308 350 C1372 320 1460 340 1515 402 C1505 470 1438 526 1360 500 C1300 478 1262 407 1308 350 Z',
    context: 'gnomAD SAS: South Asian; oriented over South Asia for map context',
  },
}

export function gnomadMapAnchor(groupId: string): GnomadMapAnchor {
  return (
    GNOMAD_ANCESTRY_MAP_ANCHORS[groupId.toLowerCase()] ??
    GNOMAD_ANCESTRY_MAP_ANCHORS.remaining
  )
}
