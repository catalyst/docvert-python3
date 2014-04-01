# -*- coding: utf-8 -*-
import os
import lxml.etree
from . import docvert_exception
from . import docvert_xml

docvert_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_pipeline_definition(pipeline_type, pipeline_id, auto_pipeline_id):
    pipeline = get_pipeline_xml(pipeline_type, pipeline_id, auto_pipeline_id)
    pipeline['stages'] = process_stage_level( pipeline['xml'].getroot() )
    return pipeline

def process_stage_level(nodes):
    stages = list()
    for child_node in nodes:
        if child_node.tag != "stage":
            continue
        child = dict()
        child['attributes'] = child_node.attrib
        child['children'] = None
        if(len(child_node) > 0):
            child['children'] = process_stage_level(child_node)
        stages.append(child)
    return stages

def get_pipeline_xml(pipeline_type, pipeline_id, auto_pipeline_id):
    path = os.path.join(docvert_root, "pipelines", pipeline_type, pipeline_id, "pipeline.xml")
    if not os.path.exists(path):
        raise docvert_exception.unrecognised_pipeline("Unknown pipeline_id '%s' (checked %s)" % (pipeline_id, path))
    autopipeline_path = None
    xml = lxml.etree.parse(path)
    if xml.getroot().tag == "autopipeline":
        if auto_pipeline_id is None:
            raise docvert_exception.unrecognised_auto_pipeline("Unknown auto pipeline '%s'" % auto_pipeline_id)
        autopipeline_path = os.path.join(docvert_root, "pipelines", "auto_pipelines", auto_pipeline_id, "pipeline.xml")
        if not os.path.exists(path):
            raise docvert_exception.unrecognised_auto_pipeline("Unknown auto pipeline '%s'" % auto_pipeline_id)
        custom_stages = lxml.etree.tostring(xml.getroot()).decode('utf-8')
        autopipeline = ""
        try:        
            autopipeline_handle = open(autopipeline_path)
        except IOError as e:
            autopipeline_path_with_default = os.path.join(docvert_root, "pipelines", "auto_pipelines", "%s.default" % auto_pipeline_id, "pipeline.xml")
            autopipeline_handle = open(autopipeline_path_with_default)
        autopipeline = autopipeline_handle.read().replace('{{custom-stages}}', custom_stages)
        autopipeline = docvert_xml.strip_encoding_declaration(autopipeline)
        xml = lxml.etree.fromstring(autopipeline)
        xml = xml.getroottree()
    return dict(xml=xml, pipeline_directory=os.path.dirname(path), path=path, autopath=autopipeline_path)

class pipeline_processor(object):
    """ Processes through a list() of pipeline_item(s) """
    def __init__(self, storage, pipeline_items, pipeline_directory, pipeline_storage_prefix=None, depth=None):
        self.storage = storage
        self.pipeline_items = pipeline_items
        self.pipeline_directory = pipeline_directory
        self.pipeline_storage_prefix = pipeline_storage_prefix
        self.depth = list() if depth is None else depth

    def start(self, pipeline_value):
        for item in self.pipeline_items:
            process = item['attributes']['process']
            namespace = 'core.pipeline_type'
            full_pipeline_type = "%s.%s" % (namespace, process.lower())
            #try:
            stage_module = __import__(full_pipeline_type, {}, {}, [full_pipeline_type.rsplit(".", 1)[-1]])
            stage_class = getattr(stage_module, process)
            stage_instance = stage_class(self.storage, self.pipeline_directory, item['attributes'], self.pipeline_storage_prefix, item['children'], self.depth)
            pipeline_value = stage_instance.stage(pipeline_value)
            #except ImportError, exception:
            #    raise exception
            #    raise docvert_exception.unknown_docvert_process('Unknown pipeline process of "%s" (at %s)' % (process, "%s.%s" % (namespace, process.lower()) ))
        return pipeline_value

