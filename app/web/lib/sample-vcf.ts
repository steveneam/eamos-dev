/**
 * Minimal demo VCF for the landing "Sample VCF →" pill.
 * GRCh38 coordinates. Inherited-retinal-disease genes (RPE65, ABCA4, USH2A)
 * give panel filtering something visible; MYBPC3 + TP53 add contrast.
 */
export const SAMPLE_VCF = `##fileformat=VCFv4.2
##reference=GRCh38
##FILTER=<ID=PASS,Description="All filters passed">
##INFO=<ID=DP,Number=1,Type=Integer,Description="Read depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	68904297	rs193922620	G	A	50	PASS	DP=42
1	94473807	rs1800553	C	T	60	PASS	DP=38
1	216420462	rs786204297	T	C	55	PASS	DP=45
1	216247785	rs111033343	G	T	48	PASS	DP=31
1	216250103	rs786205076	A	G	52	PASS	DP=36
11	47332532	rs36211723	G	A	65	PASS	DP=50
11	47365653	rs727504290	C	T	58	PASS	DP=47
17	7674220	rs28934578	C	T	70	PASS	DP=55
`

export const SAMPLE_VCF_NAME = 'sample.vcf'
