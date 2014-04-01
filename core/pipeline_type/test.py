# -*- coding: utf-8 -*-
import os
import os.path
import lxml.etree
import io
from . import pipeline_item
import core.docvert_exception
import core.docvert
import core.docvert_xml


class Test(pipeline_item.pipeline_stage):
    def stage(self, pipeline_value):
        def get_size(data):
            if hasattr(data, 'read'):
                data.seek(0, os.SEEK_END)
                return data.tell()
            return len(data)

        if not ("withFile" in self.attributes or "extensionExist" in self.attributes):
            raise no_with_file_attribute("In process Test there wasn't a withFile or extensionExist attribute.")
        if pipeline_value is None:
            raise xml_empty("Cannot Test with %s because pipeline_value is None." % self.attributes['withFile'])
        test_result = None
        if "withFile" in self.attributes:
            test_path = self.resolve_pipeline_resource(self.attributes['withFile'])
            if not os.path.exists(test_path):
                raise file_not_found("Test file not found at %s" % test_path)
            prefix = ""
            if "prefix" in self.attributes:
                prefix = "%s: " % self.attributes["prefix"]
            if test_path.endswith(".rng"): # RelaxNG test
                relaxng_response = core.docvert_xml.relaxng(pipeline_value, test_path)
                node_name = "pass"
                if not relaxng_response["valid"]:
                    node_name = "fail"
                test_result = '<group xmlns="docvert:5"><%s>%s%s</%s></group>' % (node_name, prefix, core.docvert_xml.escape_text(str(relaxng_response["log"])), node_name)
            elif test_path.endswith(".txt"): # Substring test (new substring on each line)
                document_string = str(pipeline_value)
                if hasattr(pipeline_value, "read"):
                    document_string = pipeline_value.read()
                    pipeline_value.seek(0)
                test_result = '<group xmlns="docvert:5">'
                for line in open(test_path, 'r').readlines():
                    test_string = line[0:-1].strip()
                    if len(test_string) == 0: continue
                    node_name = "fail"
                    description = "doesn't contain"
                    occurences = document_string.count(test_string)
                    if occurences == 1:
                        node_name = "pass"
                        description = "contains one of"
                    elif occurences > 1:
                        node_name = "fail"
                        description = "contains %i of" % occurences
                    test_result += '<%s>%s%s</%s>' % (node_name, prefix, core.docvert_xml.escape_text('Document %s the string "%s"' % (description, test_string)), node_name)
                test_result += '</group>'
            else: #XSLT
                test_result = core.docvert_xml.transform(pipeline_value, test_path, dict(**self.attributes))
        elif "extensionExist" in self.attributes:
            extension = self.attributes["extensionExist"]
            extension_exist_count = 1
            if "extensionExistCount" in self.attributes:
                extension_exist_count = int(self.attributes["extensionExistCount"])
            original_extension_exist_count = extension_exist_count
            for key in list(self.storage.keys()):
                if key.endswith('thumbnail.png'): #ignore any inbuilt thumbnails
                    continue
                if key.endswith(extension):
                    if self.pipeline_storage_prefix is None or (self.pipeline_storage_prefix and key.startswith(self.pipeline_storage_prefix)):
                        if get_size(self.storage[key]) > 0:
                            extension_exist_count -= 1
            test_result = "pass"
            text = 'There were %i files with the extension "%s" as expected.' % (original_extension_exist_count, extension)
            if extension_exist_count != 0:
                test_result = "fail"
                text = 'There were only %i (%i-%i) files instead of %i with the extension "%s". ' % (original_extension_exist_count - extension_exist_count, original_extension_exist_count, extension_exist_count, original_extension_exist_count, extension)
            test_result = '<group xmlns="docvert:5"><%s>%s</%s></group>' % (test_result, core.docvert_xml.escape_text(text), test_result)
        if "debug" in self.attributes:
            raise core.docvert_exception.debug_xml_exception("Test Results", str(test_result), "text/xml; charset=UTF-8")
        self.add_tests(test_result)
        return pipeline_value        


class no_with_file_attribute(core.docvert_exception.docvert_exception):
    pass

class file_not_found(core.docvert_exception.docvert_exception):
    pass

class xml_empty(core.docvert_exception.docvert_exception):
    pass
