import pysam
from q2_nasp2_types.alignment import BAMSortedAndIndexedDirFmt
import glob

def smor(alignment_map: BAMSortedAndIndexedDirFmt) -> BAMSortedAndIndexedDirFmt:
    alignment_map_fp = glob.glob(str(alignment_map.path) + "/*.bam")[0]
    samdata = pysam.AlignmentFile(alignment_map_fp, "rb")
    help(samdata)
    print(alignment_map.path)
    return samdata
