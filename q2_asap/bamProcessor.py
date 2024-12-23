import os
import re
import logging
import math
import glob

import pysam
from collections import Counter
from xml.etree import ElementTree
from skbio import DNA
from skbio.alignment import local_pairwise_align_ssw

import json
import numpy as np
import array as arr
from pathlib import Path

from q2_nasp2_types.alignment import BAMSortedAndIndexedDirFmt
from ._formats import ASAPXMLOutputDirFmt
from q2_asap.assayInfo import parseJSON


low_level_cutoff = 0.01
high_level_cutoff = 0.50
proportion = 0.1
smartSMOR = True


def pairwise(iterable):
    from itertools import tee
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def _write_parameters(node, data):
    for k, v in data.items():
        subnode = ElementTree.SubElement(node, k)
        subnode.text = str(v)
    return node


def _primer_mask(primer_file, bam_file_name, wiggle, pmaskbam, ponlybam, smor):
    # TODO: Ideally for smor it should use the same primer pair, so will have
    # to match reads and then search, will at this at some stage
    # assumptions
    # you know that primerF is on read 1 and primer R is for
    # read 2 (as you added the adapters like this)
    # you want to keep singletons (these could be easily removed later)
    logging.info("Starting primer_mask function")
    samfile = pysam.AlignmentFile(bam_file_name, "rb")
    bam_file_out = os.path.splitext(bam_file_name)[0] + '_primerMasked.bam'
    bamout = pysam.AlignmentFile(bam_file_out, "wb", template=samfile)
    # process file - add some error handling here
    try:
        primers = np.loadtxt(str(primer_file), delimiter="\t",
                             dtype={'names': ('CHROM', 'PrimerName',
                                              'PrimerDirection',
                                              'Start', 'End'),
                                    'formats': ('<U100', '<U100', 'U1',
                                                'int', 'int')}, skiprows=1)
    except ValueError:
        logging.info("Incorrect primer file format")
        return samfile
    primers["PrimerDirection"] = np.char.upper(primers["PrimerDirection"])
    primer_stats = []
    # its been converted to a string from the analyzeAmplicons input
    mask_bases = pmaskbam != 'False'
    # its been converted to a string from the analyzeAmplicons input
    ponlybam = ponlybam != 'False'
    # TODO add ponlybam option to only emit reads with primer sequence, will
    # need to deal with pairs in this case for each ref in bam
    for chrom in samfile.references:
        # check that all chroms are accounted for in input file
        if chrom in primers["CHROM"]:
            # For each primer set
            # from inputus--------
            # primers["CHROM"][primers["CHROM"] == chrom]
            forward_primer_set_strt = primers["Start"][
                np.multiply(
                    primers["CHROM"] == chrom,
                    primers["PrimerDirection"] == "F")]
            forward_primer_set_end = primers["End"][
                np.multiply(
                    primers["CHROM"] == chrom,
                    primers["PrimerDirection"] == "F")]
            reverse_primer_set_strt = primers["Start"][
                np.multiply(
                    primers["CHROM"] == chrom,
                    primers["PrimerDirection"] == "R")]
            reverse_primer_set_end = primers["End"][
                np.multiply(
                    primers["CHROM"] == chrom,
                    primers["PrimerDirection"] == "R")]
            # from inputus end--------
            forward_primer_set_strt = forward_primer_set_strt - wiggle
            reverse_primer_set_end = reverse_primer_set_end + wiggle
            # make sure no negative
            forward_primer_set_strt[forward_primer_set_strt < 0] = 0
            # make sure not longer than reference
            ref_len = samfile.get_reference_length(chrom)
            forward_primer_set_end[forward_primer_set_end > ref_len] = ref_len
            reverse_primer_set_end[reverse_primer_set_end > ref_len] = ref_len
            # check if any sequences are aligned there
            # samfile.count_coverage(
            # contig='rpoB', start=p_forward_s-wiggle, stop=p_reverse_e+wiggle)
            # if none skip
            no_primer = 0
            primer_found = 0
            for read in samfile.fetch(chrom, until_eof=True):
                # It seems this happens when only one read in the pair
                # is aligned, then the mate is still associated with the CHROM
                # but has not alignment position, causing min() to fail as no
                # value in it
                try:
                    # read.query_alignment_start (ead.query_alignment_end) is
                    # what base of the read is the first that's
                    # aligned to the reference
                    # first base of read that is aligned, might be useful if we
                    # consider that adapters have been remove, not using now
                    align_start = min(read.get_reference_positions())
                    # + read.query_alignment_start
                    align_end = max(read.get_reference_positions())
                except Exception:
                    no_primer += 1
                    # read.query_qualities = arr.array(
                    # "B", [0] * len(read.query_qualities))
                    # read.query_sequence = "N" * len(read.query_sequence)
                    # this is here as to keep pairs,
                    # the above should probably be added?
                    bamout.write(read)
                    pass
                if read.is_read1:
                    # If read aligns within 'wiggle' nts of primer sequence
                    tmp_boo = np.multiply(
                        align_start >= forward_primer_set_strt,
                        align_start <= forward_primer_set_end)
                    if any(tmp_boo):
                        primer_found += 1
                        # deal with if more than one is true using the max
                        # to deal with if whole read in in the primer section,
                        # this can happen if short reads not filtered or if
                        # incorrect primer file, and not removing as
                        # then need to remove mate;
                        # TODO should output stats to log
                        # (align_end if int(forward_primer_set_end[tmp_boo].max()) > align_end else int(forward_primer_set_end[tmp_boo].max())) - align_start + read.query_alignment_start
                        # ref pos where primer ends - first ref pos where
                        # sequence aligns + unaligned leading bases
                        mask_end = (
                            int(forward_primer_set_end[tmp_boo].max())
                            - align_start
                            + read.query_alignment_start)
                        mask_end = (
                            len(read.query_sequence)
                            if mask_end > len(read.query_sequence)
                            else mask_end)

                        read.query_qualities[:mask_end] = arr.array(
                            "B", [0] * mask_end)
                        if mask_bases:
                            qual_store = read.query_qualities
                            read.query_sequence = (
                                "N" * len(read.query_sequence[:mask_end])
                                + read.query_sequence[mask_end:])
                            read.query_qualities = qual_store
                            # read.query_sequence = (
                            # read.query_sequence[:mask_start])
                            # read.query_qualities = qual_store[:mask_start]
                            # read.cigarstring = ""
                            # read.cigartuples = ""
                    else:
                        # TODO
                        # else, mark as a fail. If fails >0 X% of reads then
                        # retry with larger wiggle?
                        no_primer += 1
                elif read.is_read2:
                    tmp_boo2 = np.multiply(
                        align_end >= reverse_primer_set_strt,
                        align_end <= reverse_primer_set_end)
                    if any(tmp_boo2):
                        primer_found += 1
                        # deal with if more than one is true using the min
                        # mask_start = (int(reverse_primer_set_strt[tmp_boo2].min())
                        # - align_start + read.query_alignment_start)
                        mask_start = (align_start if int(reverse_primer_set_strt[tmp_boo2].min()) < align_start else int(
                            reverse_primer_set_strt[tmp_boo2].min())) - align_start + read.query_alignment_start
                        read.query_qualities[mask_start:read.query_length] = arr.array(
                            "B", [0] * len(read.query_qualities[mask_start:read.query_length]))
                        if mask_bases:
                            qual_store = read.query_qualities
                            read.query_sequence = read.query_sequence[:mask_start] + "N" * len(
                                read.query_sequence[mask_start:])
                            read.query_qualities = qual_store
                            # read.query_sequence = read.query_sequence[:mask_start]
                            # read.query_qualities = qual_store[:mask_start]
                            # read.cigarstring = ""
                            # read.cigartuples = ""
                    else:
                        no_primer += 1
                else:
                    logging.debug("Aberrant read: %s" % read.query_name)
                bamout.write(read)
            primer_stats.append([chrom, primer_found, no_primer])
        else:
            logging.info("No primers found for: %s" % chrom)
            for read in samfile.fetch(chrom, until_eof=True):
                bamout.write(read)
    logging.info("CHROM, Primer Found, Primer Missing")
    logging.info(primer_stats)
    bamout.close()  # only aligned reads
    samfile.close()
    if mask_bases:  # need to sort as trimming may have changed coordinates
        bam_file_out_sorted = os.path.splitext(
            bam_file_name)[0] + '_primerMasked_sorted.bam'
        pysam.sort("-o", bam_file_out_sorted, bam_file_out)
        bam_file_out = bam_file_out_sorted
    pysam.index(bam_file_out)
    logging.info("Wrote primer masking alignment only file: ", bam_file_out)
    return pysam.AlignmentFile(bam_file_out, "rb")


def _process_pileup(pileup, amplicon, depth, proportion, mutdepth, offset,
                    wholegenome, smor, base_qual, con_prop, fill_gap_char,
                    fill_del_char):
    global low_level_cutoff, high_level_cutoff
    pileup_dict = {}
    snp_dict = _create_snp_dict(amplicon)
    deletion_counter = Counter()  # keep track of deletions by read name
    consensus_seq = ""
    if fill_gap_char:
        gapfilled_consensus_seq = ""
    snp_list = []
    breadth_positions = 0
    avg_depth_total = avg_depth_positions = 0
    amplicon_length = len(amplicon.sequence)
    depth_array = [0] * amplicon_length
    discard_array = [0] * amplicon_length
    prop_array = ["0"] * amplicon_length
    previous_position = 0
    # for each position in alignment/pileup
    for pileupcolumn in pileup:
        base_counter = Counter()
        # gets incremented if smor, gets set to depth if not smor
        depth_array[pileupcolumn.pos] = 0
        position = pileupcolumn.pos + 1
        # This fills gaps in the alignment with n's or user defined char
        if fill_gap_char:
            # We've skipped some positions in the alignment
            if previous_position + 1 < position:
                # print("%i, %i" % (previous_position, position))
                for i in range(previous_position + 1, position):
                    gapfilled_consensus_seq += fill_gap_char  # Fill in the gap
        previous_position = position
        column_depth = None
        # if smor flag
        if smor:
            from operator import attrgetter
            start_count = pileupcolumn.n
            end_count = 0
            # sorts pileups by name
            reads = iter(
                sorted(
                    pileupcolumn.pileups,
                    key=attrgetter('alignment.query_name')
                )
            )
            for read, pair in pairwise(reads):
                # keep pairs together
                if read.alignment.query_name != pair.alignment.query_name:
                    continue
                end_count = end_count + 1  # count pairs
                alignment = read.alignment
                try:
                    if read.is_del and pair.is_del:
                        # If this position is a deletion, it won't have
                        # a qscore, so lets use the average qscore of
                        # the aligned reads flanking this deletion
                        read_qscore = (read.alignment.query_qualities[read.query_position_or_next] +
                                       read.alignment.query_qualities[read.query_position_or_next - 1]) / 2
                        pair_qscore = (pair.alignment.query_qualities[pair.query_position_or_next] +
                                       pair.alignment.query_qualities[pair.query_position_or_next - 1]) / 2
                        if read_qscore >= base_qual and pair_qscore >= base_qual:
                            depth_array[pileupcolumn.pos] += 1
                            base_counter.update({"_": 1})
                        else:
                            discard_array[pileupcolumn.pos] += 1
                    # check here
                    elif read.alignment.query_qualities[read.query_position] >= base_qual and pair.alignment.query_qualities[pair.query_position] >= base_qual:
                        # Id prefer if the BSQ were recalibrated already by ddbuk
                        # bbmerge.sh in1=reads.F.fq in2=read.R.fq
                        # out1=corrected.F.fq out2=corrected.R.fq ecco mix
                        if pair.indel < 0 and read.indel < 0:  # This means the NEXT position is a deletion
                            for d in range(
                                    1, min(abs(read.indel), abs(pair.indel)) + 1):
                                deletion_counter.update({str(position + d)})
                        if pair.indel > 0 and read.indel > 0:  # This means the next position is an insertion
                            start = read.query_position
                            end = read.query_position + read.indel + 1
                            pstart = pair.query_position
                            pend = pair.query_position + pair.indel + 1
                            if pair.alignment.query_sequence[pstart:
                                                             pend] == alignment.query_sequence[start:end]:
                                depth_array[pileupcolumn.pos] += 1
                                base_counter.update(
                                    {alignment.query_sequence[start:end]: 1})
                            else:
                                discard_array[pileupcolumn.pos] += 1
                        elif read.query_position and pair.query_position:
                            if pair.alignment.query_sequence[pair.query_position] == alignment.query_sequence[read.query_position]:
                                depth_array[pileupcolumn.pos] += 1
                                base_counter.update(
                                    alignment.query_sequence[read.query_position])
                            else:
                                discard_array[pileupcolumn.pos] += 1
                    else:
                        discard_array[pileupcolumn.pos] += 1
                except Exception:
                    # print("Unexpected error:", sys.exc_info()[0])
                    discard_array[pileupcolumn.pos] += 1  # check here
                    pass
            # Don't think we need this section here anymore, being handled above.
            # Process any deletions at this position
            # if str(position) in deletion_counter:
            #    base_counter.update({"_" : deletion_counter[str(position)]})
            #    depth_array[pileupcolumn.pos] += deletion_counter[str(position)]

            column_depth = depth_array[pileupcolumn.pos]

            if column_depth == 0:
                # consensus_seq += "_" #TODO Temporary, remove this line!
                continue
            depth_passed = False
            if column_depth > 0:  # TODO: This is going to end up being specific to these TB assays, maybe have a clever way to make this line optional
                avg_depth_positions += 1
                avg_depth_total += column_depth
            if column_depth >= depth:
                breadth_positions += 1
                depth_passed = True
        else:  # not smor, doesn't sort by names
            depth_array[pileupcolumn.pos] = pileupcolumn.n
            depth_passed = False
            passed_Qual_filter = 0
            for pileupread in pileupcolumn.pileups:
                # print("processing read, qual=%i" % pileupread.alignment.query_qualities[pileupread.query_position])
                try:
                    if pileupread.is_del:
                        # This position in the alignment is a deletion in the query sequence, therefore it has no quality score
                        # Let's use the average of the quality scores of the two
                        # aligned bases flanking the deletion
                        qscore = (pileupread.alignment.query_qualities[pileupread.query_position_or_next] +
                                  pileupread.alignment.query_qualities[pileupread.query_position_or_next - 1]) / 2
                        if qscore >= base_qual:
                            passed_Qual_filter += 1
                            base_counter.update({"_": 1})
                    # check here
                    elif pileupread.alignment.query_qualities[pileupread.query_position] >= base_qual:
                        passed_Qual_filter += 1
                        if pileupread.indel < 0:  # This means the next position is a deletion, we'll process later
                            for d in range(1, abs(pileupread.indel) + 1):
                                deletion_counter.update({str(position + d)})
                        if pileupread.indel > 0:  # This means the next position is an insertion, unlike with deletions, this we can process now
                            start = pileupread.query_position
                            end = pileupread.query_position + pileupread.indel + 1
                            base_counter.update(
                                {pileupread.alignment.query_sequence[start:end]: 1})
                        else:
                            base_counter.update(
                                pileupread.alignment.query_sequence[pileupread.query_position])
                    else:
                        discard_array[pileupcolumn.pos] += 1
                except Exception:
                    # print("Unexpected error:", sys.exc_info()[0])
                    discard_array[pileupcolumn.pos] += 1  # check here
                    pass
            # Don't think we need this section here anymore, being handled above.
            # Process any deletions at this position
            # if str(position) in deletion_counter:
            #    base_counter.update({"_" : deletion_counter[str(position)]})
            #    passed_Qual_filter += deletion_counter[str(position)]

        if column_depth is None:  # this means did not do smor, so set column_depth to whole depth
            # check this, changing to the reads that possed BQS filter, doing it
            # like this as I think pileupcolumn.n is called later
            pileupcolumn.n = passed_Qual_filter
            # - failed_Qual_filter # check this, this will count bases that have been filtered out by quality?
            column_depth = pileupcolumn.n
            # reset to depth that passed qual filter
            depth_array[pileupcolumn.pos] = pileupcolumn.n
        # TODO: This is going to end up being specific to these TB assays (with
        # flanking sequence), maybe have a clever way to make this line optional
        if column_depth > 0:
            avg_depth_positions += 1
            avg_depth_total += column_depth
        if column_depth >= depth:
            breadth_positions += 1
            depth_passed = True
        ordered_list = base_counter.most_common()
        if not ordered_list:  # No coverage, should only happen here if all reads were thrown out because of quality
            consensus_seq += "N"
            if fill_gap_char:
                gapfilled_consensus_seq += "N"
            continue
        alignment_call = ordered_list[0][0]
        alignment_call_proportion = ordered_list[0][1] / column_depth
        prop_array[pileupcolumn.pos] = "%.3f" % alignment_call_proportion
        reference_call = amplicon.sequence[pileupcolumn.pos]
        if reference_call == '-':
            reference_call = '_'  # Need to use '_' instead of '-' for gaps because of XSLT
        if alignment_call != reference_call:
            snp_call = alignment_call
            snp_count = ordered_list[0][1]
            snp_call_proportion = alignment_call_proportion
        elif len(ordered_list) > 1:
            snp_call = ordered_list[1][0]
            snp_count = ordered_list[1][1]
            snp_call_proportion = ordered_list[1][1] / column_depth
        else:
            snp_call = snp_count = snp_call_proportion = None
        if smor:
            (proportion, low_level_cutoff, high_level_cutoff) = (
                _compute_thresholds_SMOR(column_depth)
            )
            # print("smartSMOR =",smartSMOR,", depth =",column_depth,", proportion =",proportion,"\n")

        # Generate consensus call at this pos
        # consensus_seq += alignment_call if alignment_call_proportion >= consensus_proportion else "N"
        # unless the alignment_call is a deletion, and >50% -- don't ever replace deletions with Ns
        # or if coverage is less than the depth threshold, then always call N
        if not depth_passed:  # N's if we don't have enough coverage
            consensus_seq += "N"
            if fill_gap_char:
                gapfilled_consensus_seq += "N"
        elif alignment_call != "_":
            if alignment_call_proportion >= con_prop:
                consensus_seq += alignment_call
                if fill_gap_char:
                    gapfilled_consensus_seq += alignment_call
            else:  # Consensus proportion not high enough
                consensus_seq += "N"
                if fill_gap_char:
                    gapfilled_consensus_seq += "N"
        else:
            if alignment_call_proportion <= 0.5:  # Verify that the gap call is truly greater than 50%
                consensus_seq += "N"
                if fill_gap_char:
                    gapfilled_consensus_seq += "N"
            else:
                if fill_del_char:  # Put in gaps if user requested them
                    consensus_seq += fill_del_char
                    if fill_gap_char:
                        gapfilled_consensus_seq += fill_del_char
        # if the offset is negative, ie. amplicon starts before beginning
        # of the gene, then when converting to gene-based coordinates need to
        # make offset 1 unit more positive to account for there being no 0-base
        # in gene-coordinates
        if position >= abs(offset) and offset < 0:
            translated = position + (offset + 1)
        else:
            # normal case where gene encompasses the amplicon
            translated = position + offset
        if position in snp_dict:
            for (name, reference, variant, significance) in snp_dict[position]:
                snp = {'name': name, 'position': str(translated),
                       'depth': str(column_depth), 'reference': reference,
                       'variant': variant, 'basecalls': base_counter}
                variant_proportion = base_counter[variant] / column_depth
                variant_count = base_counter[variant]
                if variant_proportion >= proportion and variant_count >= mutdepth:
                    snp['significance'] = significance
                    if smor:
                        if variant_proportion <= low_level_cutoff:
                            snp['level'] = "low"
                        elif variant_proportion >= high_level_cutoff:
                            snp['level'] = "high"
                if not depth_passed:
                    snp['flag'] = "low coverage"
                snp_list.append(snp)
            # We've covered it, now remove it from the dict
            # so we can see what we might have missed
            del snp_dict[position]
        elif depth_passed and snp_call and snp_count >= mutdepth and snp_call_proportion >= proportion:
            snp = {'name': 'unknown', 'position': str(translated),
                   'depth': str(column_depth), 'reference': reference_call,
                   'variant': snp_call, 'basecalls': base_counter}
            if 0 in snp_dict:
                (name, *rest, significance) = snp_dict[0][0]
                snp['name'] = name
                snp['significance'] = significance
            snp_list.append(snp)
    # Check for any positions_of_interest that weren't covered
    snp_dict.pop(0, None)
    for position in snp_dict.keys():
        for (name, reference, variant, significance) in snp_dict[position]:
            snp = {'name': name, 'position': str(position), 'depth': str(0),
                   'reference': reference, 'variant': variant}
            snp_list.append(snp)
    # If reference is whole genome, none of these are going to make sense,
    # and they will make the output too large
    if not wholegenome:
        pileup_dict['consensus_sequence'] = consensus_seq
        if fill_gap_char:
            pileup_dict['gapfilled_consensus_sequence'] = gapfilled_consensus_seq
        pileup_dict['depths'] = ",".join(str(n) for n in depth_array)
        pileup_dict['proportions'] = ",".join(prop_array)
    pileup_dict['breadth'] = str(breadth_positions / amplicon_length * 100)
    if smor:
        pileup_dict['discards'] = ",".join(str(n) for n in discard_array)
    pileup_dict['SNPs'] = snp_list
    pileup_dict['average_depth'] = str(
        avg_depth_total / avg_depth_positions) if avg_depth_positions else "0"
    return pileup_dict


def _create_snp_dict(amplicon):
    snp_dict = {}
    for snp in amplicon.SNPs:
        name = snp.name if snp.name else "position of interest"
        if not snp.variant or snp.variant == "any":
            for v in {'A', 'G', 'C', 'T'}:
                if v != snp.reference:
                    if snp.position in snp_dict:
                        snp_dict[snp.position].append((name, snp.reference, v,
                                                       snp.significance))
                    else:
                        snp_dict[snp.position] = [(name, snp.reference, v,
                                                   snp.significance)]
        else:
            if snp.position in snp_dict:
                snp_dict[snp.position].append((name, snp.reference,
                                               snp.variant, snp.significance))
            else:
                snp_dict[snp.position] = [(name, snp.reference, snp.variant,
                                           snp.significance)]
    return snp_dict


def _add_snp_node(parent, snp):
    snp_attributes = {
        k: snp[k]
        for k in ('name', 'position', 'depth', 'reference')}
    snp_node = ElementTree.SubElement(parent, 'snp', snp_attributes)
    base_counter = snp.get('basecalls')
    snpcall = snp['variant']
    depth = int(snp['depth'])
    snpcount = base_counter[snpcall] if base_counter else 0
    percent = snpcount / depth * 100 if depth else 0
    snpcall_node = ElementTree.SubElement(
        snp_node,
        'snp_call',
        {'count': str(snpcount), 'percent': str(percent)})
    snpcall_node.text = snpcall
    if 'significance' in snp or 'flag' in snp:
        significance_node = ElementTree.SubElement(snp_node, 'significance')
        if 'significance' in snp:
            significance_node.text = snp['significance'].message
            if snp['significance'].resistance:
                significance_node.set(
                    "resistance",
                    snp['significance'].resistance)
            if 'level' in snp:
                significance_node.set("level", snp['level'])
        if 'flag' in snp:
            significance_node.set('flag', snp['flag'])
    if base_counter:
        ElementTree.SubElement(
            snp_node,
            'base_distribution',
            {k: str(v) for k, v in base_counter.items()})
    return snp_node


def _process_roi(roi, samdata, amplicon_ref, smor, amplicon_ref_len,
                 reverse_comp=False):
    from operator import attrgetter
    roi_dict = {'region': roi.position_range}
    range_match = re.search('(\\d*)-(\\d*)', roi.position_range)
    if not range_match:
        return roi_dict
    start = int(range_match.group(1)) - 1
    end = int(range_match.group(2))
    if end < start:
        reverse_comp = True
        start, end = end, start
    expected_length = end - start
    # check if the roi spans the whole reference, if so can
    # use .query_alignment_sequence to get the whole sequence without
    # running into the problem of the loop not getting to last base
    # still will have a problem when start != 0 but end == amplicon_ref_len
    use_query_alignment_seq = False
    if end == amplicon_ref_len and start == 0:
        use_query_alignment_seq = True
    aligned_reads = samdata.fetch(amplicon_ref, start, end)
    big_reads = []
    # check if reads are long enough, if not then merge
    n = failed = 0
    for read, pair in pairwise(aligned_reads):
        if read.reference_end is None or read.reference_start is None:
            continue
        n += 1
        if read.reference_end - read.reference_start < (expected_length * 0.9):
            failed += 1
    if n == 0:
        roi_dict['flag'] = "region not found"
        return roi_dict
    elif not smor:  # no --smor flag
        proportion_failed = failed / n
        if proportion_failed >= .95:
            logging.debug("reads are not as big as roi, merging...")
            reads = sorted(
                samdata.fetch(amplicon_ref, start, end),
                key=attrgetter('query_name'))
            big_reads = _process_merge(reads, start, end)
    else:  # smor
        proportion_failed = failed / n
        if proportion_failed >= .95:
            roi_dict['flag'] = (
                "reads are smaller than ROI and cannot merge because --smor")
            return roi_dict
    aa_sequence_counter = Counter()
    aa_sequence_counter_temp = Counter()
    nt_sequence_counter = Counter()
    depth = 0
    significant = False
    if not roi.aa_sequence:
        roi.aa_sequence = (
            str(DNA(roi.nt_sequence).translate()).replace('*', 'x'))
    if big_reads != []:  # merged => not smor
        for read in big_reads:
            nt_sequence = DNA(read)
            if reverse_comp:
                nt_sequence = nt_sequence.reverse_complement()
            if nt_sequence.has_degenerates():
                continue
            aa_sequence = nt_sequence.translate()
            aa_string = str(aa_sequence).replace('*', 'x')
            if aa_string:
                nt_sequence_counter.update([str(nt_sequence)])
                aa_sequence_counter_temp.update([aa_string])
                depth += 1
    elif not smor:  # no --smor flag
        aligned_reads = samdata.fetch(amplicon_ref, start, end)
        for read in aligned_reads:
            rstart = read.reference_start
            rend = read.reference_end
            # alignment_length = read.get_overlap(start, end)
            # throw out reads that either have gaps in
            # the ROI or don't cover the whole ROI
            # if alignment_length != expected_length:
            #    continue
            # Keep reads with indels, but do throw out reads that
            # don't cover whole ROI
            if not rend or rstart > start or rend < end:
                continue
            if rstart <= start:
                if not use_query_alignment_seq:
                    qend = qstart = None
                    for (qpos, rpos) in read.get_aligned_pairs():
                        if rpos == start:
                            qstart = qpos
                        if rpos == end:
                            qend = qpos
                    nt_sequence = DNA(read.query_sequence[qstart:qend])
                else:
                    # the ROI is the whole ref so
                    # can use .query_alignment_sequence
                    nt_sequence = DNA(read.query_alignment_sequence)
                if reverse_comp:
                    nt_sequence = nt_sequence.reverse_complement()
                # scikit-bio doesn't support translating degenerate bases
                # currently, so we will just throw out reads with
                # degenerates for now
                if nt_sequence.has_degenerates():
                    continue
                aa_sequence = nt_sequence.translate()
                aa_string = str(aa_sequence).replace('*', 'x')
                if aa_string:
                    nt_sequence_counter.update([str(nt_sequence)])
                    aa_sequence_counter_temp.update([aa_string])
                    depth += 1
    else:  # smor
        reads = iter(sorted(
            samdata.fetch(amplicon_ref, start, end),
            key=attrgetter('query_name')))
        for read, pair in pairwise(reads):
            if read.query_name != pair.query_name:
                continue
            nt_sequence = nt_sequence2 = None
            rstart1 = read.reference_start
            rstart2 = pair.reference_start
            rend1 = read.reference_end
            rend2 = pair.reference_end
            alignment_length1 = read.get_overlap(start, end)
            alignment_length2 = pair.get_overlap(start, end)
            # Throw out reads that are not the same length as their pair
            if alignment_length1 != alignment_length2:
                continue
            # Throw out reads that don't cover the whole ROI
            if (
                not rend1
                or not rend2
                or rstart1 > start
                or rstart2 > start
                or rend1 < end
                or rend2 < end
            ):
                continue
            if rstart1 <= start:
                if not use_query_alignment_seq:
                    qend = qstart = None
                    for (qpos, rpos) in read.get_aligned_pairs():
                        if rpos == start:
                            qstart = qpos
                        if rpos == end:
                            qend = qpos
                    nt_sequence = DNA(read.query_sequence[qstart:qend])
                else:
                    # the ROI is the whole ref so
                    # can use .query_alignment_sequence
                    nt_sequence = DNA(read.query_alignment_sequence)
            if rstart2 <= start:
                if not use_query_alignment_seq:
                    qend = qstart = None
                    for (qpos, rpos) in pair.get_aligned_pairs():
                        if rpos == start:
                            qstart = qpos
                        if rpos == end:
                            qend = qpos
                    nt_sequence2 = DNA(pair.query_sequence[qstart:qend])
                else:
                    # the ROI is the whole ref so
                    # can use .query_alignment_sequence
                    nt_sequence2 = DNA(pair.query_alignment_sequence)
            if (
                not nt_sequence
                or not nt_sequence2
                or nt_sequence != nt_sequence2
            ):
                continue
            else:
                if reverse_comp:
                    nt_sequence = nt_sequence.reverse_complement()
                # scikit-bio doesn't support translating degenerate bases
                # currently, so we will just throw out reads with
                # degenerates for now
                if nt_sequence.has_degenerates():
                    continue
                aa_sequence = nt_sequence.translate()
                aa_string = str(aa_sequence).replace('*', 'x')
                if aa_string:
                    nt_sequence_counter.update([str(nt_sequence)])
                    aa_sequence_counter_temp.update([aa_string])
                    depth += 1
    if len(aa_sequence_counter_temp) == 0:
        roi_dict['flag'] = "region not found"
        return roi_dict
    else:
        for (aa_string, count) in aa_sequence_counter_temp.most_common():
            num_changes = 0
            for i in range(len(roi.aa_sequence)):
                if len(aa_string) <= i or roi.aa_sequence[i] != aa_string[i]:
                    num_changes += 1
            aa_sequence_counter[(aa_string, num_changes)] = count
    # This next bit is just being saved for backward compatibility. Should
    # deprecate and remove soon
    (aa_consensus, num_changes) = aa_sequence_counter.most_common(1)[0][0]
    nt_consensus = nt_sequence_counter.most_common(1)[0][0]
    reference = roi.aa_sequence
    consensus = aa_consensus
    if roi.nt_sequence:
        reference = roi.nt_sequence
        consensus = nt_consensus
    roi_dict['most_common_aa_sequence'] = aa_consensus
    roi_dict['most_common_nt_sequence'] = nt_consensus
    roi_dict['reference'] = reference
    roi_dict['changes'] = str(num_changes)
    # End backward compatibility code
    roi_dict['aa_sequence_distribution'] = aa_sequence_counter
    roi_dict['nt_sequence_distribution'] = nt_sequence_counter
    roi_dict['depth'] = str(depth)
    return roi_dict


def _add_roi_node(parent, roi, roi_dict, depth, proportion, mutdepth,
                  smor, offset, allele_min_reads):
    global low_level_cutoff, high_level_cutoff
    nonsynonymous = False
    if "flag" in roi_dict:
        roi_node = _add_dummy_roi_node(parent, roi)
        significance_node = ElementTree.SubElement(
            roi_node, "significance", {'flag': roi_dict['flag']})
        if roi.significance.resistance:
            significance_node.set("resistance", roi.significance.resistance)
        return roi_node
    # Smart SMOR -- thresholds and proportion filter are a function of the
    # number of SMOR reads at position
    if smor:
        (
            proportion, low_level_cutoff, high_level_cutoff
        ) = _compute_thresholds_SMOR(int(roi_dict['depth']))

    roi_attributes = {k: roi_dict[k] for k in ('region', 'reference', 'depth')}
    roi_attributes['name'] = str(roi.name)
    roi_node = ElementTree.SubElement(
        parent, "region_of_interest", roi_attributes)
    if not roi.aa_sequence:
        roi.aa_sequence = str(
            DNA(roi.nt_sequence).translate()).replace('*', 'x')
    roi_node.set('aa_reference', roi.aa_sequence)
    reporting_threshold = max(mutdepth, math.ceil(
        int(roi_dict['depth']) * proportion))
    cutOff = int(roi_dict['depth']) * .02
    range_match = re.search('(\\d*)-(\\d*)', roi.position_range)
    start = int(range_match.group(1)) - 1
    end = int(range_match.group(2))
    if end < start:
        reverse_comp = True
        start, end = end, start
    dominant_count = 0
    # Number of reads containing the
    # most common amino acid sequence
    aa_seq_counter = roi_dict['aa_sequence_distribution']

    # calculate offsets depending on if in positive region of gene or negative
    # adding one when in negative to keep consistent with _process_pileup
    aa_offset_pos = math.floor(offset / 3)
    aa_offset_neg = math.floor((offset + 1) / 3)
    for ((seq, aa_changes), count) in aa_seq_counter.most_common():
        if dominant_count == 0:
            dominant_count = count
        if count >= reporting_threshold:
            aa_seq_node = ElementTree.SubElement(
                roi_node, "amino_acid_sequence", {
                    'count': str(count),
                    'percent': str(count / int(roi_dict['depth']) * 100),
                    'aa_changes': str(aa_changes)})
            aa_seq_node.text = seq
            if aa_changes > 0:
                nonsynonymous = True
            # get string of the aa changes
            changes = []
            all_changes = []
            for i in range(len(roi.aa_sequence)):
                if i > len(seq) - 1:
                    change = [i, roi.aa_sequence[i], "_"]
                    all_changes.append(change)
                    changes.append(change)
                elif roi.aa_sequence[i] != seq[i]:
                    change = [i, roi.aa_sequence[i], seq[i]]
                    all_changes.append(change)
                    changes.append(change)
            if len(seq) > len(roi.aa_sequence):
                for i in range(len(roi.aa_sequence), len(seq)):
                    change = [i, "_", seq[i]]
                    all_changes.append(change)
                    changes.append(change)
            # check to see if aa changes are a result of an indel, and if so
            # remove them
            start_of_run = _sequential(changes, 0)
            changes = changes[0:start_of_run]
            shift = 0
            # create change string with '1' and '2' that will be replaced by
            # <b><u> and </u></b> in post-processing
            for change in all_changes:
                loc = change[0] + shift
                # check if change is past last base in seq => an indel at the
                # end of seq
                if loc >= len(seq):
                    temp = seq + '1' + '_' + '2'
                else:
                    temp = seq[0:loc] + '1' + seq[loc] + '2' + seq[loc + 1:]
                shift += 2
                seq = temp
            aa_seq_node.set('underline_seq', seq)
            # create changes strings, adjusting the aa coordinates to be
            # gene-relative
            if all_changes != []:
                change_string = ""
                for all_change in all_changes:
                    # if the offset is negative, ie. amplicon starts before
                    # beginning of the gene, then when converting to gene-based
                    # coordinates need to make offset 1 unit more positive to
                    # account for there being no 0-base in gene-coordinates
                    if all_change[0] >= abs(
                            aa_offset_pos) and aa_offset_pos < 0:
                        all_change[0] = all_change[0] + aa_offset_neg
                    else:
                        # normal case where gene encompasses the amplicon
                        all_change[0] = all_change[0] + aa_offset_pos
                    change_string += ', ' + \
                        all_change[1] + str(all_change[0]) + all_change[2]
                aa_seq_node.set('aa_changes_specific_all', change_string)
                change_string = ""
                for change in changes:
                    # don't need to shift the aa coordinates here again because
                    # all_changes and changes are filled with same,
                    # shallow copied, lists
                    if change[0] < 0:
                        continue
                    else:
                        change_string += change[1] + \
                            str(change[0]) + change[2] + ', '
                aa_seq_node.set('aa_changes_specific', change_string)
        else:
            # Since they are returned in order by count, as soon as one is
            # below the threshold the rest will be as well
            break

    nt_seq_counter = roi_dict['nt_sequence_distribution']
    skbio_reference = None
    if roi.nt_sequence:
        skbio_reference = DNA(roi.nt_sequence)
    for (seq, count) in nt_seq_counter.most_common():
        if count >= reporting_threshold:
            nt_seq_node = ElementTree.SubElement(
                roi_node, "nucleotide_sequence",
                {'count': str(count),
                 'percent': str(
                    count / int(roi_dict['depth']) * 100)})
            nt_seq_node.text = seq
            if skbio_reference:
                # align to reference
                alignment, score, pos_range = local_pairwise_align_ssw(
                        skbio_reference, DNA(seq))
                # get string of the nt changes
                changes = []
                all_changes = []
                i = 1
                for aligned_seq_pos in alignment.iter_positions():
                    if str(aligned_seq_pos[1]) == '-':
                        change = [i + start, str(aligned_seq_pos[0]), "_"]
                        all_changes.append(change)
                        changes.append(change)
                        i = i + 1
                    elif str(aligned_seq_pos[0]) == '-':
                        change = [i + start, "_", str(aligned_seq_pos[1])]
                        all_changes.append(change)
                        changes.append(change)
                        # Don't advance the counter for gaps in the reference
                    elif aligned_seq_pos[0] != aligned_seq_pos[1]:
                        change = [
                            i + start, str(aligned_seq_pos[0]),
                            str(aligned_seq_pos[1])
                            ]
                        all_changes.append(change)
                        changes.append(change)
                        i = i + 1
                    else:
                        i = i + 1
                shift = 0
                # create change string with '1' and '2' that will be replaced
                # by <b><u> and </u></b> in post-processing
                for change in all_changes:
                    loc = change[0] - start - 1 + shift
                    temp = seq
                    if change[2] == '_':
                        temp = seq[0:loc] + '1' + '_' + '2' + seq[loc:]
                    elif change[1] == '_':
                        # What do we do with insertions
                        continue
                    else:
                        temp = seq[0:loc] + '1' + seq[loc] + '2' + seq[loc + 1:]
                    shift += 2
                    seq = temp
                nt_seq_node.set('underline_seq', seq)
                # create changes strings, adjusting the nt coordinates
                # to be gene-relative
                if all_changes != []:
                    change_string = ""
                    for all_change in all_changes:
                        # if the offset is negative, ie. amplicon starts
                        # before beginning of the gene, then when converting to
                        # gene-based coordinates need to make offset 1 unit
                        # more positive to account for there being
                        # no 0-base in gene-coordinates
                        if all_change[0] >= abs(offset) and offset < 0:
                            all_change[0] = all_change[0] + (offset + 1)
                        else:
                            # normal case where gene encompasses the amplicon
                            all_change[0] = all_change[0] + offset
                        change_string += ', ' + \
                            all_change[1] + str(all_change[0]) + all_change[2]
                    nt_seq_node.set('nt_changes_specific_all', change_string)
                    change_string = ""
                    for change in changes:
                        # don't need to shift the nt coordinates here again
                        # because all_changes and changes are filled with same,
                        # shallow copied, lists
                        if change[0] < 0:
                            continue
                        else:
                            change_string += (
                                change[1] + str(change[0]) + change[2] + ', ')
                    nt_seq_node.set('nt_changes_specific', change_string)
            else:
                # If we don't have a reference NT sequence,
                # then we can't display the changes
                continue
        else:
            # Since they are returned in order by count, as soon as one is
            # below the threshold the rest will be as well
            break

    allele_count = 0
    for (seq, count) in nt_seq_counter.most_common():
        # get most frequent alleles that have a freq of > 2% (this is an
        # arbitrary cut-off)
        if count >= cutOff:
            allele_node = ElementTree.SubElement(
                roi_node, "allele_sequence",
                {'count': str(count),
                 'percent': str(count / int(roi_dict['depth']) * 100),
                 'hash': str(hash(seq))})
            allele_node.text = seq
            allele_count += 1
        else:
            if allele_count < 2:
                allele_count += 1
                allele_node = ElementTree.SubElement(
                    roi_node, "allele_sequence",
                    {'count': str(count),
                     'percent': str(count / int(roi_dict['depth']) * 100),
                     'hash': str(hash(seq))
                     })
                allele_node.text = seq
            else:
                break
    low_level = True
    high_level = False
    significant = False
    for mutation in roi.mutations:
        if roi.nt_sequence:
            count = nt_seq_counter[mutation]
            mutant_proportion = count / int(roi_dict['depth'])
        else:
            count = aa_seq_counter[next(
                (k for k in aa_seq_counter.keys() if k[0] == mutation), None)]
            mutant_proportion = count / int(roi_dict['depth'])
        mutation_node = ElementTree.SubElement(
            roi_node,
            'mutation',
            {'name': str(roi.name) + mutation,
             'count': str(count),
             'percent': str(mutant_proportion * 100)})
        mutation_node.text = mutation
        if mutant_proportion >= proportion and count >= mutdepth:
            significant = True
            if mutant_proportion > low_level_cutoff:
                low_level = False
            if mutant_proportion >= high_level_cutoff:
                high_level = True
    if significant:
        significance_node = ElementTree.SubElement(roi_node, "significance")
        significance_node.text = roi.significance.message
        if roi.significance.resistance:
            significance_node.set("resistance", roi.significance.resistance)
        if int(roi_dict['depth']) < depth:
            significance_node.set("flag", "low coverage")
        if low_level:
            significance_node.set("level", "low")
        elif high_level:
            significance_node.set("level", "high")
    elif len(roi.mutations) == 0 and dominant_count >= mutdepth and (
            ('changes' in roi_dict and int(roi_dict['changes']) > 0)
            or nonsynonymous):
        significance_node = ElementTree.SubElement(
            roi_node, "significance", {'changes': roi_dict['changes']})
        significance_node.text = roi.significance.message
        if roi.significance.resistance:
            significance_node.set("resistance", roi.significance.resistance)
        # that is so incredibly strange that i am typing that habitualy
        if int(roi_dict['depth']) < depth:
            significance_node.set("flag", "low coverage")
    # No significance but still need to flag it for low coverage
    elif int(roi_dict['depth']) < depth:
        significance_node = ElementTree.SubElement(roi_node, "significance")
        if roi.significance.resistance:
            significance_node.set("resistance", roi.significance.resistance)
        significance_node.set("flag", "low coverage")
    # keep all alleles until this point so proportional calculations are correct
    # do not output alleles that have less than allele_min_reads # of reads
    # key is a tuple of (sequence, changes) and I just want the sequence
    ElementTree.SubElement(
        roi_node, 'aa_sequence_distribution',
        {k[0]: str(v)
         for k, v in aa_seq_counter.items()
         if v >= allele_min_reads})
    ElementTree.SubElement(
        roi_node, 'nt_sequence_distribution',
        {k: str(v)
         for k, v in nt_seq_counter.items()
         if v >= allele_min_reads})
    return roi_node


# returns the index of the start of a run of sequential numbers
# from some point in array to the end of array
# if such a run does not exist it returns the index of last element + 1
# allows for one element gaps,
# ie. [1,3,4,5,6] would return 0 but [1,4,5,6] would return 1
def _sequential(arr, n):
    if n == len(arr) - 1:
        return n + 1
    for i in range(n, len(arr) - 1):
        if arr[i][0] + 1 != arr[i + 1][0] and arr[i][0] + 2 != arr[i + 1][0]:
            return _sequential(arr, i + 1)
    return n


def _add_dummy_roi_node(parent, roi):
    reference = roi.aa_sequence
    if roi.nt_sequence:
        reference = roi.nt_sequence
    roi_attributes = {'region': roi.position_range, 'name': str(roi.name),
                      'reference': reference, 'depth': "0"}
    roi_node = ElementTree.SubElement(
        parent, "region_of_interest", roi_attributes)
    for mutation in roi.mutations:
        mutation_node = ElementTree.SubElement(
            roi_node, 'mutation',
            {'name': str(roi.name) + mutation, 'count': "0", 'percent': "0"})
        mutation_node.text = mutation
    return roi_node


def _compute_thresholds_SMOR(smor_count):
    global smartSMOR, proportion, low_level_cutoff, high_level_cutoff
    if not smartSMOR:
        # Use user-specified proportion and default cutoff values
        return (proportion, low_level_cutoff, high_level_cutoff)
    # else use smartSMOR
    proportion = 0
    low_level_cutoff = 0
    high_level_cutoff = 0
    if smor_count >= 5000:
        proportion = 0.001
        low_level_cutoff = 0.01
        high_level_cutoff = 0.5
    elif smor_count >= 500:
        proportion = 0.01
        low_level_cutoff = 0.01
        high_level_cutoff = 0.5
    elif smor_count >= 50:
        proportion = 0.1
        low_level_cutoff = 0.1
        high_level_cutoff = 0.5
    elif smor_count >= 25:
        proportion = 0.2
        low_level_cutoff = 0.2
        high_level_cutoff = 0.5
    return (proportion, low_level_cutoff, high_level_cutoff)


def _process_merge(reads, start, end):
    big_aligned_reads = []
    for read, pair in pairwise(reads):
        if read.query_name != pair.query_name:
            continue
        refstart1 = read.reference_start
        refend1 = read.reference_end
        refstart2 = pair.reference_start
        refend2 = pair.reference_end
        if (
            refstart1 is None
            or refend1 is None
            or refstart2 is None
            or refend2 is None
        ):
            continue
        # get the farthest left and right positions that
        # either read align to reference
        refstart = refstart1 if refstart1 < refstart2 else refstart2
        refend = refend2 if refend2 > refend1 else refend1
        combined_read = ""
        for ref_pos in range(refstart, refend):
            read_base = pair_base = None
            for (read_qpos, read_rpos) in read.get_aligned_pairs():
                if read_rpos == ref_pos and read_qpos is not None:
                    read_base = str(DNA(read.query_sequence[int(read_qpos)]))
                    read_qual = read.query_qualities[int(read_qpos)]
                    break
            for (pair_qpos, pair_rpos) in pair.get_aligned_pairs():
                if pair_rpos == ref_pos and pair_qpos is not None:
                    pair_base = str(DNA(pair.query_sequence[int(pair_qpos)]))
                    pair_qual = pair.query_qualities[int(pair_qpos)]
                    break
            if read_base is None and pair_base is None:
                combined_read += 'N'
            elif read_base is not None and pair_base is None:
                combined_read += read_base
            elif read_base is None and pair_base is not None:
                combined_read += pair_base
            else:
                if read_qual >= pair_qual:
                    combined_read += read_base
                else:
                    combined_read += pair_base
        if len(combined_read) == end - start:
            big_aligned_reads.append(combined_read)
    return big_aligned_reads


def _merge_reads(read, pair):
    from copy import deepcopy
    rstart = read.query_alignment_start
    rend = read.query_alignment_end
    pstart = pair.query_alignment_start
    pend = pair.query_alignment_end
    merged_read = deepcopy(read)
    if pstart <= rend:  # There is overlap that will need to be processed
        pass
    if pstart > rend + 1:  # There is a gap that will need to be filled with Ns
        pass


def _verify_percent_identity(samdata, ref_name, amplicon, percid, merge):
    temp_file = "%s_%s_temp.bam" % (os.path.splitext(
        os.path.basename(samdata.filename.decode("utf-8")))[0], ref_name)
    outdata = pysam.AlignmentFile(temp_file, "wb", template=samdata)
    amp_length = len(amplicon.sequence)
    discarded_reads = 0
    seq_counter = Counter()
    aligned_reads = []
    logging.debug(
        "Checking %s for amplicon %s, length %i" % (samdata.filename,
                                                    ref_name, amp_length))
    if merge:
        from operator import attrgetter
        reads = iter(sorted(
            samdata.fetch(ref_name),
            key=attrgetter('query_name')))
        for read, pair in pairwise(reads):
            if read.alignment.query_name != pair.alignment.query_name:
                continue
            aligned_reads.append(_merge_reads(read, pair))
    else:
        aligned_reads = samdata.fetch(ref_name)
    for read in aligned_reads:
        if read.is_unmapped:
            logging.debug("\tRead is unmapped, skipping....")
            continue
        length = read.infer_query_length(False)
        # reset amp_length in case we altered it in the last iteration
        amp_length = len(amplicon.sequence)
        logging.debug("Read %s, aligned length %i, total read length %i" %
                      (read.query_name,
                       read.query_alignment_length or -1, length or -1))
        # Using length instead of amp_length to compare to query
        # instead of reference
        if read.query_alignment_length / length >= percid:
            matches = 0
            for (qpos, rpos, seq) in read.get_aligned_pairs(with_seq=True):
                query = read.query_sequence[qpos] if qpos else "None"
                logging.debug(
                    "\tqpos: %i\trpos: %i\tseq: %s\tquery[qpos]: %s" %
                    (qpos or -1, rpos or -1, seq, query)
                )
                # if there is a gap in the alignment, extend the length of the
                # query or reference accordingly
                if rpos is None:
                    amp_length += 1
                elif qpos is None:
                    length += 1
                else:
                    if read.query_sequence[qpos].upper() == seq.upper():
                        matches += 1
            # Using length instead of amp_length to compare to
            # query instead of reference
            if matches / length >= percid:
                logging.debug("\t\tFound %i matches, keeping..." % matches)
                outdata.write(read)
            else:
                logging.debug("\t\tFound %i matches, discarding..." % matches)
                discarded_reads += 1
                seq_counter.update([read.query_sequence])
        else:
            logging.debug("\t\tToo short, discarding...")
            discarded_reads += 1
            seq_counter.update([read.query_sequence])
    outdata.close()
    pysam.index(temp_file)
    return (temp_file, discarded_reads, seq_counter)


class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''

    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


def bamProcessor(alignment_map: BAMSortedAndIndexedDirFmt,
                 config_file_path: str) -> ASAPXMLOutputDirFmt:

    global smartSMOR, proportion

    try:
        # open and load config file path
        config = open(config_file_path)
        data = json.load(config)

        # load data into params
        bamProcessor = data["ASAP_parameters"]["bamProcessor"]

        json_fp = bamProcessor["json"]  # JSON file of assay descriptions
        depth = bamProcessor["depth"]
        breadth = bamProcessor["breadth"]
        proportion = bamProcessor["proportion"]
        mutdepth = bamProcessor["mutation_depth"]
        percid = bamProcessor["percid"]
        keep = bamProcessor["keep"]
        merge = bamProcessor["merge"]
        smor = bamProcessor["smor"]
        debug = bamProcessor["debug"]
        allele_min_reads = bamProcessor["allele_min_reads"]
        wholegenome = bamProcessor["whole_genome"]
        primer_mask_file = bamProcessor["primer_mask"]
        wiggle = bamProcessor["primer_wiggle"]
        pmaskbam = bamProcessor["primer_mask_bam"]
        ponlybam = bamProcessor["primer_only_bam"]
        base_qual = bamProcessor["min_base_qual"]
        con_prop = bamProcessor["consensus_proportion"]
        fill_gap_char = bamProcessor["gap_char"]
        fill_del_char = bamProcessor["del_char"]

        if smor:
            if proportion > 0.0:
                # Turn off smartSMOR if user explicitly sets proportion flag
                smartSMOR = False
            else:
                proportion = 0.001  # Set SMOR default
        else:
            if proportion <= 0.0:
                proportion = 0.1  # Set default if user did not specify

        assay_list = parseJSON(json_fp)
        # TODO: dont leave this line validate only one is found
        alignment_map_fp = glob.glob(str(alignment_map.path) + "/*.bam")[0]
        samdata = pysam.AlignmentFile(alignment_map_fp, "rb")

        sample_dict = {}
        if 'RG' in samdata.header.to_dict():
            sample_dict['name'] = samdata.header.to_dict()['RG'][0]['ID']
        else:
            sample_dict['name'] = os.path.splitext(
                os.path.basename(alignment_map_fp))[0]
        sample_dict['mapped_reads'] = str(samdata.mapped)
        sample_dict['unmapped_reads'] = str(samdata.unmapped)
        sample_dict['unassigned_reads'] = str(samdata.nocoordinate)
        sample_dict['depth_filter'] = str(depth)
        # When doing SMOR analysis, proportion filter will be a function of
        # SMOR count at a given position/ROI, and will ignore passed-in value.
        # Let's specifically set to zero, to make sure all get reported.
        if smor:
            sample_dict['SMOR'] = 'True'
        sample_dict['proportion_filter'] = str(proportion)
        sample_dict['breadth_filter'] = str(breadth)
        sample_dict['mutation_depth_filter'] = str(mutdepth)
        if percid:
            sample_dict['identity_filter'] = str(percid)
        # minidom.parseString will raise xml.parsers.expat.ExpatError:
            # not well-formed (invalid token)
        # if json_file or bam_file contain the python string representation
            #  of a file-like object.
        # e.g. bam_file="<_io.BufferedReader
        #  name=\'/shared/Targeted_sequence_fastqs/ASAP/COD-10-24_S302.bam\'>"
        sample_dict['json_file'] = json_fp
        sample_dict['bam_file'] = alignment_map_fp
        sample_node = ElementTree.Element("sample", sample_dict)

        if debug:
            # Remove all handlers associated with the root logger object.
            # for handler in logging.root.handlers[:]:
            #    logging.root.removeHandler(handler)

            logfile = "%s.log" % sample_dict['name']

            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s %(levelname)-8s %(message)s',
                datefmt='%m/%d/%Y %H:%M:%S',
                filename=logfile,
                filemode='w')
        # its been converted to a string from the analyzeAmplicons input
        if primer_mask_file != 'False' and not wholegenome:
            samdata = _primer_mask(primer_file=primer_mask_file,
                                   bam_file_name=str(alignment_map_fp),
                                   wiggle=wiggle, pmaskbam=pmaskbam,
                                   ponlybam=ponlybam, smor=smor)

        for assay in assay_list:
            assay_dict = {}
            assay_dict['name'] = assay.name
            assay_dict['type'] = assay.assay_type
            assay_dict['function'] = assay.target.function or ""
            assay_dict['gene'] = assay.target.gene_name or ""
            assay_dict['start'] = assay.target.start_position or ""
            assay_dict['end'] = assay.target.end_position or ""
            # offset is where the amplicon sits relative to a reference,
            # subtract 1 to make 0-based position
            # report the lesser of start and end
            # in case amplicon is on reverse strand
            try:
                offset = min(
                    int(assay.target.start_position),
                    int(assay.target.end_position)) - 1
                ref_positions = list(
                    range(min(int(assay.target.start_position),
                              int(assay.target.end_position)),
                          max(int(assay.target.start_position),
                              int(assay.target.end_position)) + 1))
                # remove the zero if present
                if 0 in ref_positions:
                    ref_positions.remove(0)
            except BaseException:
                offset = 0
                ref_positions = None
            assay_node = ElementTree.SubElement(
                sample_node, "assay", assay_dict)
            ref_name = assay.name
            reverse_comp = assay.target.reverse_comp
            for amplicon in assay.target.amplicons:
                if not ref_positions:
                    ref_positions = list(range(1, len(amplicon.sequence) + 1))
                temp_file = None
                ref_name = (
                                assay.name +
                                "_%s" % amplicon.variant_name
                                if amplicon.variant_name
                                else assay.name
                            )
                amplicon_dict = {}
                seq_counter = None
                if percid:
                    (
                        temp_file,
                        discarded_reads,
                        seq_counter
                        ) = _verify_percent_identity(
                        samdata, ref_name, amplicon, percid, merge)
                    samdata = pysam.AlignmentFile(temp_file, "rb")
                    amplicon_dict['discarded_reads'] = str(discarded_reads)
                elif samdata.closed:
                    samdata = pysam.AlignmentFile(alignment_map_fp, "rb")
                amplicon_dict['reads'] = str(samdata.count(ref_name))
                if amplicon.variant_name:
                    amplicon_dict['variant'] = amplicon.variant_name
                amplicon_node = ElementTree.SubElement(assay_node, "amplicon",
                                                       amplicon_dict)
                if keep and seq_counter:
                    ElementTree.SubElement(
                        amplicon_node, "sequence_distribution",
                        {k: str(v) for k, v in seq_counter.items()})
                if samdata.count(ref_name) == 0:
                    significance_node = ElementTree.SubElement(
                        amplicon_node, "significance", {"flag": "no coverage"})
                    # Check for indeterminate resistances
                    resistances = set()
                    if (
                        amplicon.significance
                        and amplicon.significance.resistance
                    ):
                        resistances.add(amplicon.significance.resistance)
                    for snp in amplicon.SNPs:
                        name = snp.name if snp.name else "position of interest"
                        dummy_snp = {'name': name,
                                     'position': str(snp.position),
                                     'depth': "0", 'reference': snp.reference,
                                     'variant': snp.variant, 'basecalls': None}
                        _add_snp_node(amplicon_node, dummy_snp)
                        if snp.significance.resistance:
                            resistances.add(snp.significance.resistance)
                    for roi in amplicon.ROIs:
                        _add_dummy_roi_node(amplicon_node, roi)
                        if roi.significance.resistance:
                            resistances.add(roi.significance.resistance)
                    if resistances:
                        significance_node.set(
                            "resistance",
                            ",".join(resistances))
                else:
                    if amplicon.significance or samdata.count(ref_name) < depth:
                        significance_node = ElementTree.SubElement(
                            amplicon_node, "significance")
                        if amplicon.significance:
                            significance_node.text = (
                                amplicon.significance.message)
                            if amplicon.significance.resistance:
                                significance_node.set(
                                    "resistance",
                                    amplicon.significance.resistance)
                        if samdata.count(ref_name) < depth:
                            significance_node.set("flag", "low coverage")
                            # Check for indeterminate resistances
                            resistances = set()
                            if (
                                    amplicon.significance
                                    and amplicon.significance.resistance):
                                resistances.add(
                                    amplicon.significance.resistance)
                            for snp in amplicon.SNPs:
                                if snp.significance.resistance:
                                    resistances.add(
                                        snp.significance.resistance)
                            for roi in amplicon.ROIs:
                                if roi.significance.resistance:
                                    resistances.add(
                                        roi.significance.resistance)
                            if resistances:
                                significance_node.set("resistance",
                                                      ",".join(resistances))
                    pileup = samdata.pileup(ref_name, max_depth=10000000,
                                            ignore_orphans=False,
                                            ignore_overlaps=False)
                    amplicon_data = _process_pileup(pileup, amplicon, depth,
                                                    proportion, mutdepth,
                                                    offset, wholegenome,
                                                    smor, base_qual, con_prop,
                                                    fill_gap_char,
                                                    fill_del_char)
                    if float(amplicon_data['breadth']) < breadth * 100:
                        significance_node = amplicon_node.find("significance")
                        if significance_node is None:
                            significance_node = ElementTree.SubElement(
                                amplicon_node, "significance")
                        if not significance_node.get("flag"):
                            significance_node.set(
                                "flag", "insufficient breadth of coverage")
                    for snp in amplicon_data['SNPs']:
                        _add_snp_node(amplicon_node, snp)
                        # This would be helpful, but count_coverage is broken
                        #  in python3 -- TODO: Revisit this
                        # print(samdata.count_coverage(
                        # ref_name,snp.position-1, snp.position))
                    del amplicon_data['SNPs']
                    _write_parameters(amplicon_node, amplicon_data)
                    if not wholegenome:
                        ref_positions_node = ElementTree.SubElement(
                            amplicon_node, "ref_positions")
                        ref_positions_node.text = ",".join(
                            str(n) for n in ref_positions)
                    for roi in amplicon.ROIs:
                        roi_dict = _process_roi(roi, samdata, ref_name, smor,
                                                len(amplicon.sequence),
                                                reverse_comp)
                        _add_roi_node(amplicon_node, roi, roi_dict, depth,
                                      proportion, mutdepth, smor, offset,
                                      allele_min_reads)
                if temp_file:
                    samdata.close()
                    os.remove(temp_file)
                    os.remove(temp_file + ".bai")
                    samdata = pysam.AlignmentFile(alignment_map_fp, "rb")

        if samdata.is_open():
            samdata.close()

        xml_output_artifact = ASAPXMLOutputDirFmt()
        output_file_path = Path(xml_output_artifact.path) / Path(
            os.path.splitext(os.path.basename(alignment_map_fp))[0] + ".xml")

        with open(output_file_path, 'w') as file_obj:
            _write_output(file_obj, sample_node)

    except KeyboardInterrupt:
        pass

    return xml_output_artifact


def _write_output(file_obj, xml_element):

    from xml.dom import minidom
    dom = minidom.parseString(ElementTree.tostring(xml_element))
    file_obj.write(dom.toprettyxml(indent="  "))


# cast_json_output_types is a json decoder object_hook intended to be used on
# a ASAP output decoded from XML:
# - casts numbers from strings to float/int
# - keys that are expected to contain 0 to n elements are lists (or undefined)
#   eliminating the 1 element object case.
# - As a special addition, values that were stored in the XML as strings of
#   comma separated values are converted to an array of an appropriate type.
def cast_json_output_types(e):
    # Sample
    if '@breadth_filter' in e:
        e['@breadth_filter'] = float(e['@breadth_filter'])
    if '@depth_filter' in e:
        e['@depth_filter'] = int(e['@depth_filter'])
    # @json_file
    if '@mapped_reads' in e:
        e['@mapped_reads'] = int(e['@mapped_reads'])
    # @name
    if '@proportion_filter' in e:
        e['@proportion_filter'] = float(e['@proportion_filter'])
    if '@unassigned_reads' in e:
        e['@unassigned_reads'] = int(e['@unassigned_reads'])
    if '@unmapped_reads' in e:
        e['@unmapped_reads'] = int(e['@unmapped_reads'])
    if 'assay' in e and not isinstance(e['assay'], list):
        e['assay'] = [(e['assay'])]

    # Assay
    # @function
    # @gene
    # @name
    # @type
    # amplicon
    if 'amplicon' in e and not isinstance(e['amplicon'], list):
        e['amplicon'] = [e['amplicon']]

    # Amplicon
    if '@reads' in e:
        e['@reads'] = int(e['@reads'])
    # if 'significance' in e and not isinstance(e['significance'], dict):
    # consensus_sequence
    if 'breadth' in e:
        e['breadth'] = float(e['breadth'])
    if 'depths' in e:
        e['depths'] = [int(v) for v in e['depths'].split(',')]
    if 'proportions' in e:
        e['proportions'] = [float(v) for v in e['proportions'].split(',')]
    if 'average_depth' in e:
        e['average_depth'] = float(e['average_depth'])
    if 'snp' in e and not isinstance(e['snp'], list):
        e['snp'] = [e['snp']]
    if (
        'region_of_interest' in e
        and not isinstance(e['region_of_interest'], list)
    ):
        e['region_of_interest'] = [e['region_of_interest']]

    # SNP
    if '@depth' in e:
        e['@depth'] = int(e['@depth'])
    # @name
    if '@position' in e:
        e['@position'] = int(e['@position'])
    # @reference
    # snp_call
    if 'base_distribution' in e:
        e['base_distribution'] = {
            k: int(v)
            for k, v in e['base_distribution'].items()}

    # SnpCall
    if '@count' in e:
        e['@count'] = int(e['@count'])
    if '@percent' in e:
        e['@percent'] = float(e['@percent'])
    # #text: "T"

    # RegionOfInterest
    # TODO: what if {aa,nt}_sequence_distribution is set and None;
        # should it default to an empty array? undefined? none?
    if e.get('aa_sequence_distribution'):
        e['aa_sequence_distribution'] = {
            k: int(v)
            for k, v in e['aa_sequence_distribution'].items()}
    if e.get('nt_sequence_distribution'):
        e['nt_sequence_distribution'] = {
            k: int(v)
            for k, v in e['nt_sequence_distribution'].items()}
    if '@changes' in e:
        e['@changes'] = int(e['@changes'])
    if 'mutation' in e and not isinstance(e['mutation'], list):
        e['mutation'] = [e['mutation']]

    # Significance
    if 'significance' in e and isinstance(e['significance'], str):
        e['significance'] = {'#text': e['significance']}
    if '@resistance' in e:
        e['@resistance'] = e['@resistance'].split(',')

    return e
