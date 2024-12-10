from qiime2.plugin.model import DirectoryFormat, TextFileFormat, FileCollection


class ASAPXMLFormat(TextFileFormat):

    def _validate_(self, level):
        pass


class ASAPXMLOutputDirFmt(DirectoryFormat):
    xml_files = FileCollection(
        r'.*xml',
        format=ASAPXMLFormat
    )

    @xml_files.set_path_maker
    def sequences_path_maker(self, sample_id):
        return f"{sample_id}.xml"


class ASAPHTMLFormat(TextFileFormat):

    def _validate_(self, level):
        pass


class ASAPHTMLOutputDirFmt(DirectoryFormat):

    html_files = FileCollection(
        r'.*html',
        format=ASAPHTMLFormat
    )

    @html_files.set_path_maker
    def sequences_path_maker(self, sample_id):
        return f"{sample_id}.html"


class FormattedOutputFormat(TextFileFormat):

    def _validate_(self, level):
        pass


class FormattedOutputDirFmt(DirectoryFormat):

    html_files = FileCollection(
        r'*.*',
        format=FormattedOutputFormat
    )

    @html_files.set_path_maker
    def sequences_path_maker(self, sample_id):
        return f"{sample_id}.html"


class ASAPJSONFormat(TextFileFormat):

    def _validate_(self, level):
        pass


class ASAPJSONOutputDirFmt(DirectoryFormat):

    json_files = FileCollection(
        r'.*json',
        format=ASAPJSONFormat
    )

    @json_files.set_path_maker
    def sequences_path_maker(self, sample_id):
        return f"{sample_id}.json"
