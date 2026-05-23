export interface GnomadMapAnchor {
  x: number
  y: number
  context: string
}

export const GNOMAD_ANCESTRY_MAP_VERSION = 'eamos-gnomad-ancestry-map-v1'

// Eamos proprietary visual anchor layer: gnomAD group labels describe
// source genetic-similarity cohorts, not patient ancestry or exact geography.
export const GNOMAD_ANCESTRY_MAP_ANCHORS: Record<string, GnomadMapAnchor> = {
  afr: {
    x: 1040,
    y: 510,
    context: 'gnomAD AFR: African / African American; oriented over Africa for map context',
  },
  ami: {
    x: 505,
    y: 300,
    context: 'gnomAD AMI: Amish founder population; oriented over North America for map context',
  },
  amr: {
    x: 575,
    y: 500,
    context: 'gnomAD AMR: Admixed American; oriented over the Americas for map context',
  },
  asj: {
    x: 1135,
    y: 285,
    context:
      'gnomAD ASJ: Ashkenazi Jewish; diaspora group, oriented near Europe / Middle East for map context',
  },
  eas: {
    x: 1530,
    y: 315,
    context: 'gnomAD EAS: East Asian; oriented over East Asia for map context',
  },
  fin: {
    x: 1105,
    y: 160,
    context: 'gnomAD FIN: Finnish; oriented over Finland / northern Europe for map context',
  },
  mid: {
    x: 1270,
    y: 335,
    context: 'gnomAD MID: Middle Eastern; oriented over the Middle East for map context',
  },
  nfe: {
    x: 1045,
    y: 235,
    context: 'gnomAD NFE: European, non-Finnish; oriented over Europe for map context',
  },
  remaining: {
    x: 1010,
    y: 410,
    context: 'gnomAD RMI: Remaining individuals not assigned to current gnomAD labels',
  },
  rmi: {
    x: 1010,
    y: 410,
    context: 'gnomAD RMI: Remaining individuals not assigned to current gnomAD labels',
  },
  sas: {
    x: 1375,
    y: 400,
    context: 'gnomAD SAS: South Asian; oriented over South Asia for map context',
  },
}

export function gnomadMapAnchor(groupId: string): GnomadMapAnchor {
  return (
    GNOMAD_ANCESTRY_MAP_ANCHORS[groupId.toLowerCase()] ??
    GNOMAD_ANCESTRY_MAP_ANCHORS.remaining
  )
}

