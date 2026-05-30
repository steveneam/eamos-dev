// gnomAD basemap — country → geographic-group mapping (plans/gnomad-map-redesign.md T2).
//
// Build-time INPUT for the basemap generator (scripts/build-gnomad-basemap.mjs,
// T3). Maps Natural Earth (world-atlas `countries-50m`) numeric ISO 3166-1 ids to
// the 7 GEOGRAPHIC gnomAD genetic-ancestry groups. NOTHING here ships to the
// client bundle: T3 dissolves each group's member-country polygons into one
// land-clipped region, projects it, and emits `gnomadMapGeometry.generated.ts`;
// the app imports only that generated asset.
//
// IMPORTANT — these are cartographic ORIENTATION regions, not claims about any
// individual's ancestry, race, or geography. gnomAD groups are genetic-similarity
// COHORTS (the framing copy in `gnomadAncestryMap.ts` is preserved). Where the
// gnomAD cohort does NOT represent a region's modern population, that region is
// deliberately LEFT OFF (it renders as plain base land, not a tracked-grey
// region) — see the JUDGMENT CALLS block below. A region appears grey only when
// it IS a tracked group but the queried variant has no AF for it (D5).
//
// Erasable-only TypeScript (type annotations + `as const`; no enums/namespaces)
// so Node 24's default type-stripping lets the `.mjs` generator `import` this
// `.ts` directly in T3. ids are stored as numbers; the generator coerces each
// feature's string id via `Number(geom.id)` (handles leading zeros, e.g. "004").
//
// ── JUDGMENT CALLS surfaced for Steven's review (T2 gate) ───────────────────
//  1. North Africa (Morocco, Algeria, Tunisia, Libya, Egypt, W. Sahara) → MID,
//     not AFR. gnomAD AFR = African/African-American (Sub-Saharan); MENA is
//     genetically closer to MID. Flag if you'd rather grey these out.
//  2. USA + Canada → BASE LAND (uncolored), NOT amr. gnomAD AMR = "Admixed
//     American" (Latino); US/Canada populations distribute across nfe/afr/eas/…
//     North America stays neutral. CONFIRMED by Steven 2026-05-31.
//  3. Southeast Asia (Vietnam, Thailand, Laos, Cambodia, Myanmar, Malaysia,
//     Singapore, Indonesia, Philippines, Brunei, Timor-Leste) → EAS.
//     CONFIRMED 2026-05-31 against the 1000 Genomes EAS super-population that
//     gnomAD's EAS classifier is anchored on: it explicitly includes KHV (Kinh,
//     Ho Chi Minh City, Vietnam) and CDX (Dai, Xishuangbanna) — i.e. Indochina /
//     SE-Asian populations — alongside CHB/CHS (Han) and JPT (Japanese). The
//     5-way continental scheme (afr/amr/eas/eur/sas) has no separate SE-Asian
//     group and SAS = the Indian subcontinent only, so SE Asia maps to EAS.
//     Oceania (PNG / Pacific) is a distinct lineage with no gnomAD group → stays
//     base land (call 10).
//  4. Russia → BASE LAND. Spans Europe + North Asia; ambiguous to color as one
//     European cohort.
//  5. Central Asia (Kazakhstan, Uzbekistan, Turkmenistan, Tajikistan,
//     Kyrgyzstan) → BASE LAND. Not cleanly any single gnomAD cohort.
//  6. Caucasus (Georgia, Armenia, Azerbaijan) → MID, for visual continuity
//     between Turkey and Iran.
//  7. Afghanistan → SAS (Central/South Asian border case).
//  8. Cyprus + N. Cyprus → MID (East Mediterranean; sits among Levant/Turkey).
//  9. Greenland → BASE LAND (Inuit population; Danish administration only).
// 10. Oceania (Australia, NZ, PNG, Pacific islands) → BASE LAND (no gnomAD
//     group). Antarctica excluded.
// 11. Caribbean: sovereign / major nations → amr; sub-national specks
//     (Aruba, Curaçao, Sint Maarten, BVI, USVI, Cayman, etc.) left base land.
// 12. Maldives → SAS (beyond the D3 six). Mauritius/Seychelles/Comoros → AFR by
//     geography despite large South-Asian-descended populations.
//
// NON-geographic groups (ami, asj, remaining) are NEVER placed on the map — they
// render as off-map chips (D6). See NON_GEOGRAPHIC_GROUPS below.

export type GnomadGeographicGroup =
  | 'afr'
  | 'amr'
  | 'eas'
  | 'fin'
  | 'mid'
  | 'nfe'
  | 'sas'

// gnomAD groups that have NO geographic basemap region (founder / diaspora /
// residual cohorts). Rendered as off-map chips, never painted on the map (D6).
export const NON_GEOGRAPHIC_GROUPS = ['ami', 'asj', 'remaining'] as const

// Natural Earth numeric ISO 3166-1 id → geographic gnomAD group.
// Sorted ascending within each group; sub-region comments aid the T2 review.
export const REGION_COUNTRIES: Record<GnomadGeographicGroup, number[]> = {
  // Finnish — Finland (+ Åland folded in to avoid a Gulf-of-Bothnia speck).
  fin: [246, 248],

  // Non-Finnish European — Europe minus Finland.
  nfe: [
    8, // Albania
    20, // Andorra
    40, // Austria
    56, // Belgium
    70, // Bosnia and Herz.
    100, // Bulgaria
    112, // Belarus
    191, // Croatia
    203, // Czechia
    208, // Denmark
    233, // Estonia
    234, // Faeroe Is.
    250, // France
    276, // Germany
    300, // Greece
    336, // Vatican
    348, // Hungary
    352, // Iceland
    372, // Ireland
    380, // Italy
    428, // Latvia
    438, // Liechtenstein
    440, // Lithuania
    442, // Luxembourg
    470, // Malta
    492, // Monaco
    498, // Moldova
    499, // Montenegro
    528, // Netherlands
    578, // Norway
    616, // Poland
    620, // Portugal
    642, // Romania
    674, // San Marino
    688, // Serbia
    703, // Slovakia
    705, // Slovenia
    724, // Spain
    752, // Sweden
    756, // Switzerland
    804, // Ukraine
    807, // Macedonia (North Macedonia)
    826, // United Kingdom
    831, // Guernsey
    832, // Jersey
    833, // Isle of Man
  ],

  // Middle Eastern — Levant, Arabian Peninsula, Anatolia, Iran, Caucasus,
  // + North Africa / Maghreb (judgment call 1) + Cyprus (call 8).
  mid: [
    12, // Algeria
    31, // Azerbaijan
    48, // Bahrain
    51, // Armenia
    196, // Cyprus
    268, // Georgia
    275, // Palestine
    364, // Iran
    368, // Iraq
    376, // Israel
    400, // Jordan
    414, // Kuwait
    422, // Lebanon
    434, // Libya
    504, // Morocco
    512, // Oman
    634, // Qatar
    682, // Saudi Arabia
    732, // W. Sahara
    760, // Syria
    784, // United Arab Emirates
    788, // Tunisia
    792, // Turkey
    818, // Egypt
    887, // Yemen
  ],

  // South Asian — Indian subcontinent (+ Afghanistan, call 7; + Maldives, call 12).
  sas: [
    4, // Afghanistan
    50, // Bangladesh
    64, // Bhutan
    144, // Sri Lanka
    356, // India
    462, // Maldives
    524, // Nepal
    586, // Pakistan
  ],

  // East Asian — China / Japan / Korea / Mongolia / Taiwan + all of Southeast
  // Asia (call 3: 1000G EAS panel includes Vietnamese KHV + Dai CDX). Oceania
  // stays base land (call 10).
  eas: [
    96, // Brunei
    104, // Myanmar
    116, // Cambodia
    156, // China
    158, // Taiwan
    344, // Hong Kong
    360, // Indonesia
    392, // Japan
    408, // North Korea
    410, // South Korea
    418, // Laos
    446, // Macao
    458, // Malaysia
    496, // Mongolia
    608, // Philippines
    626, // Timor-Leste
    702, // Singapore
    704, // Vietnam
    764, // Thailand
  ],

  // Admixed American — Latin America + Caribbean (US/Canada excluded, call 2).
  amr: [
    28, // Antigua and Barb.
    32, // Argentina
    44, // Bahamas
    52, // Barbados
    68, // Bolivia
    76, // Brazil
    84, // Belize
    152, // Chile
    170, // Colombia
    188, // Costa Rica
    192, // Cuba
    212, // Dominica
    214, // Dominican Rep.
    218, // Ecuador
    222, // El Salvador
    308, // Grenada
    320, // Guatemala
    328, // Guyana
    332, // Haiti
    340, // Honduras
    388, // Jamaica
    484, // Mexico
    558, // Nicaragua
    591, // Panama
    600, // Paraguay
    604, // Peru
    630, // Puerto Rico
    659, // St. Kitts and Nevis
    662, // Saint Lucia
    670, // St. Vin. and Gren.
    740, // Suriname
    780, // Trinidad and Tobago
    858, // Uruguay
    862, // Venezuela
  ],

  // African / African-American — Sub-Saharan Africa (North Africa → mid, call 1).
  afr: [
    24, // Angola
    72, // Botswana
    108, // Burundi
    120, // Cameroon
    132, // Cabo Verde
    140, // Central African Rep.
    148, // Chad
    174, // Comoros
    178, // Congo
    180, // Dem. Rep. Congo
    204, // Benin
    226, // Eq. Guinea
    231, // Ethiopia
    232, // Eritrea
    262, // Djibouti
    266, // Gabon
    270, // Gambia
    288, // Ghana
    324, // Guinea
    384, // Côte d'Ivoire
    404, // Kenya
    426, // Lesotho
    430, // Liberia
    450, // Madagascar
    454, // Malawi
    466, // Mali
    478, // Mauritania
    480, // Mauritius
    508, // Mozambique
    516, // Namibia
    562, // Niger
    566, // Nigeria
    624, // Guinea-Bissau
    646, // Rwanda
    678, // São Tomé and Principe
    686, // Senegal
    690, // Seychelles
    694, // Sierra Leone
    706, // Somalia
    710, // South Africa
    716, // Zimbabwe
    728, // S. Sudan
    729, // Sudan
    748, // eSwatini
    768, // Togo
    800, // Uganda
    834, // Tanzania
    854, // Burkina Faso
    894, // Zambia
  ],
}

// A handful of world-atlas features carry NO numeric id; assign them by
// `properties.name`. (Unlisted name-only features — "Indian Ocean Ter.",
// "Siachen Glacier" — stay base land.)
export const REGION_COUNTRIES_BY_NAME: Record<string, GnomadGeographicGroup> = {
  Kosovo: 'nfe',
  'N. Cyprus': 'mid',
  Somaliland: 'afr',
}
