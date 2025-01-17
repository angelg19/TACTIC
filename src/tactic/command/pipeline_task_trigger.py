###########################################################
#
# Copyright (c) 2010, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#
__all__ = ['PipelineTaskStatusTrigger', 'PipelineTaskTrigger', 'PipelineTaskDateTrigger', 'PipelineTaskCreateTrigger', 'RelatedTaskUpdateTrigger', 'TaskCreatorTrigger', 'TaskCompleteTrigger', 'PipelineParentStatusTrigger']

import tacticenv

from pyasm.common import Common, Xml, jsonloads, Container, TacticException
from pyasm.biz import Task
from pyasm.web import Widget, WebContainer, WidgetException
from pyasm.command import Command, CommandException, Trigger
from pyasm.security import Sudo

from tactic.command import PythonTrigger

from pyasm.biz import Pipeline, Task
from pyasm.search import Search, SObject, SearchKey

class PipelineTaskStatusTrigger(Trigger):
    # if the "ingest" task is set to "Approved",
    # then set the "work" task to "Pending"
    SAMPLE_DATA = {
        'src_process':  'ingest',
        'src_status':   'Approved',
        'dst_process':  'work',
        'dst_status':   'Pending',
    }


    def execute(self):
        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        data = jsonloads(data)

        data_list = data
        if isinstance(data, dict):
            data_list = [data]
        src_task = self.get_caller()
        for data in data_list:
            # get the src task caller
            dst_task = None
            # it could be the FileCheckin Command
            if not isinstance(src_task, SObject):
                input = self.get_input()
                snapshot = input.get('snapshot')

                if not snapshot:
                    continue
                if isinstance(snapshot, dict):
                    snapshot = SearchKey.get_by_search_key(snapshot.get('__search_key__'))
                src_process = data.get('src_process')
                
                src_task = Search.eval("@SOBJECT(parent.sthpw/task['process','%s'])"%src_process,\
                    sobjects=snapshot, single=True)
                if not src_task:
                    continue

            # make sure the caller process is the same as the source process
            src_process = data.get("src_process")
            if src_process and src_task.get_value("process") != src_process:
                continue

            #conditionx = "@GET(.status) != 'Approved'"
            #result = Search.eval(conditionx, src_task)
            #print("result: ", result)

            # make sure that the appropriate status was set
            src_status = data.get("src_status")
            if src_status and src_task.get_value("status") != src_status:
                continue

            # Execute script if necessary 
            script_path = trigger_sobj.get_value("script_path")
            if script_path:
                cmd = PythonTrigger(script_path=script_path)
                cmd.set_input(self.input)
                cmd.set_output(self.input)
                cmd.execute()
                continue

            # Execute trigger if necessary
            class_path = data.get("class_path")
            if class_path:
                trigger = Common.create_from_class_path(class_path)
                trigger.set_input(self.input)
                trigger.set_output(self.input)
                trigger.execute()
                continue

            # If no script was execute,then assume other task
            # statuses should be updated.

            dst_process = data.get("dst_process")
            dst_status = data.get("dst_status")

            sobject = src_task.get_parent()
            tasks = Task.get_by_sobject(sobject)

            updated_tasks = []
            use_parent = data.get("use_parent")
            if use_parent in [True,'true']:
                parent = sobject.get_parent()
                parent_tasks = Task.get_by_sobject(parent, dst_process)

                condition = data.get("condition")
                if not condition:
                    condition = "all"

                if condition == "all":
                    condition_met = True
                    for task in tasks:
                        if src_task.get_value("status") != src_status:
                            condition_met = False

                elif condition == "any":
                    condition_met = False
                    for task in tasks:
                        if task.get_value("status") == src_status:
                            condition_met = True
                            break

                if condition_met:
                    for task in parent_tasks:
                        if task.get_value("process") == dst_process:
                            updated_tasks.append(task)

            else:
                for task in tasks:
                    if task.get_value("process") == dst_process:
                        updated_tasks.append(task)


            for task in updated_tasks:
                if task.get_value("process") == dst_process:
                    task.set_value("status", dst_status)
                    task.commit()


            """
            # find the task with the appropriate process
            if src_task.get_value("process") == dst_process:
                dst_task = src_task

            # get the output and input tasks
            if not dst_task:
                output_tasks = src_task.get_output_tasks()

                for task in output_tasks:
                    if task.get_value("process") == dst_process:
                        dst_task = task
                        break

            if not dst_task:
                input_tasks = src_task.get_input_tasks()
                for task in input_tasks:
                    if task.get_value("process") == dst_process:
                        dst_task = task
                        break

            if not dst_task:
                continue

            dst_status = data.get("dst_status")

            dst_task.set_value("status", dst_status)
            dst_task.commit()


            """

class PipelineTaskTrigger(Trigger):
    '''This is the trigger that is executed on a change'''

    ARGS_KEYS = {
    }


    def execute(self):

        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        #data = """[
        #{ "prefix": "rule", "name": "status", "value": "Approved" },
        #{ "prefix": "rule", "name": "pipeline" "value": "model" },
        #{ "prefix": "action", "type": "output", "name": "status", "value": "Pending" }
        #]
        #"""

        data = jsonloads(data)
        print("data: ", data)
        from tactic.ui.filter import FilterData
        filter_data = FilterData(data)

        task = self.get_caller()

        # check that the process is correct
        trigger_info = filter_data.get_values_by_index("trigger")
        process = trigger_info.get("process")

        if task.get_value("process") != process:
            return



        parent = None

        rules = filter_data.get_values_by_prefix("rule")

        # go through each rule and determine if this trigger applies
        is_valid = True
        for rule in rules:
            attribute = rule.get('name')
            value = rule.get('value')

            if attribute in ['status']:
                # if condition does not match
                if task.get_value(attribute) != value:
                    is_valid = False

            elif attribute in ['pipeline']:
                attribute = 'pipeline_code'
                if parent == None:
                    parent = task.get_parent()
                    if parent == None:
                        continue

                if parent.get_value(attribute) != value:
                    is_valid = False

            else:
                is_valid = False

        if not is_valid:
            return



        # update the data

        #input = self.get_input()
        #update_data = input.get('update_data')
        #status = update_data.get('status')
        #search_key = input.get('search_key')
        #task = Search.get_by_search_key(search_key)


        # get the next process tasks
        output_tasks = task.get_output_tasks()
        input_tasks = task.get_input_tasks()
        actions = filter_data.get_values_by_prefix("action")
        #print("actions: ", actions)

        for action in actions:
            type = action.get("type")
            attribute = action.get('name')
            value = action.get('value')

            if type == 'output':
                for output_task in output_tasks:
                    #output_status = output_task.get_value("status")
                    output_task.set_value(attribute, value)
                    output_task.commit()


            elif type == 'input':
                for output_task in output_tasks:
                    print("a : ", attribute, value)
                    
                    #output_status = output_task.get_value("status")
                    output_task.set_value(attribute, value)
                    output_task.commit()


            elif type == 'process':
                process = action.get("process")

                for input_task in input_tasks:
                    task_process = input_task.get_value("process")
                    if task_process == process:
                        input_task.set_value(attribute, value)
                        input_task.commit()
                        break

                for output_task in output_tasks:
                    task_process = output_task.get_value("process")
                    if task_process == process:
                        output_task.set_value(attribute, value)
                        output_task.commit()
                        break
                

class PipelineParentStatusTrigger(Trigger):
    '''This is the trigger that is executed on a change'''

    ARGS_KEYS = {
    }


    def execute(self):

        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        data = jsonloads(data)

        dst_status = data.get('dst_status')

        item = self.get_caller()

        parent = item.get_parent()
        if not parent:
            return

        parent.set_value("status", dst_status)
        parent.commit()



 
class PipelineTaskDateTrigger(Trigger):
    '''This is the trigger that is executed on a change'''

    ARGS_KEYS = {
    }


    def execute(self):

        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        #data = """
        #{ "columns": [column1, column2]
        #"""

        data = jsonloads(data)

        column = data.get('column')
        src_status = data.get('src_status')

        

        item = self.get_caller()


        if isinstance(item, SObject):
            if isinstance(item, Task):
                if src_status != None:
                    if item.get_value("status") != src_status:
                        return

                item.set_now(column)
                item.commit()

            #Item can be a note when trigger input is adding or modifying notes
            else:
                process = item.get_value('process')
                expr = '@SOBJECT(parent.sthpw/task["process","%s"])'%process
                tasks = Search.eval(expr, sobjects=[item])

                if tasks:
                    for task in tasks:
                        task.set_now(column)
                        task.commit()

        #item can be a command such as check-in                 
        else:
            if hasattr(item, 'process'):
                process = item.process
                expr = '@SOBJECT(sthpw/task["process","%s"])'%process
                tasks = Search.eval(expr, sobjects=[item.sobject])

                if tasks:
                    for task in tasks:
                        task.set_now(column)
                        task.commit()
            

class RelatedTaskUpdateTrigger(Trigger):
    '''This is called on every task change.  It syncronizes tasks with
    the same context'''
    def execute(self):

        # DISABLING this ... this is a rather tenuous trigger that attempts to allow for
        # tasks to be "connected" to each other in a way that makes it look like you have
        # multiple people assigned to a task.  While this may be desireable, the mechanism
        # used below checks for the same process and context to identify tasks tat are connected.
        # This is too broad and should be done more explicitly rather than implicitly
        return

        sudo = Sudo()

        input = self.get_input()
        search_key = input.get("search_key")
        update_data = input.get("update_data")
        mode = input.get("mode")
        if mode in ['insert','delete','retire']:
            return

        task = Search.get_by_search_key(search_key)

        process = task.get_value("process")
        context = task.get_value("context")
        parent = task.get_parent()


        # find all of the tasks with the same parent and same context
        search = Search("sthpw/task")
        search.add_parent_filter(parent)
        search.add_filter("process", process)
        search.add_filter("context", context)
        tasks = search.get_sobjects()

        trigger_dict = Container.get('RelatedTaskUpdateTrigger')
        if not trigger_dict:
            trigger_dict = {}

        for attr, value in update_data.items():
            # skip assigned as this is the only difference between related tasks
            if attr == 'assigned':
                continue
            # update_data could have the post-conversion value None
            if value == None:
                value = ''

            for task in tasks:
                task_search_key = task.get_search_key()
                # skip the current one
                if task_search_key == search_key or trigger_dict.get(task_search_key):
                    continue
                task.set_value(attr, value)
                trigger_dict[task_search_key] = True
                Container.put('RelatedTaskUpdateTrigger', trigger_dict)
                # this should run trigger where applicable
                task.commit(triggers=True)

        del sudo







class PipelineTaskCreateTrigger(Trigger):
    
    def execute(self):
        input = self.get_input()

        search_key = input.get("search_key")
        task = Search.get_by_search_key(search_key)
        parent = task.get_parent()
        if not parent:
            raise TacticException("Task parent not found.")

        # get the definition of the trigger
        trigger_sobj = self.get_trigger_sobj()
        data = trigger_sobj.get_value("data")
        try:
            data = jsonloads(data)
        except:
            raise TacticException("Incorrect formatting of trigger [%s]." % trigger_sobj.get_value("code"))

        # check against source status if present 
        src_status = data.get("src_status")
        if src_status:
            task_status = task.get_value("status")
            if task_status != src_status:
                return

        process_names = data.get("output")
        if not process_names:
            return

        Task.add_initial_tasks(parent, parent.get_value('pipeline_code'), processes=process_names,
                               contexts=process_names, skip_duplicate=True, mode='standard', start_offset=0)







class TaskCreatorTrigger(Trigger):
    '''This is executed on every insert of an sobject'''


    def has_been_called(self, prev_called_triggers):
        return False

    def execute(self):

        input = self.get_input()
       
        search_key = input.get("search_key")
        update_data = input.get("update_data")

        if not search_key or search_key.startswith('sthpw/'):
            return

        mode = input.get("mode")
        if mode not in ['insert']:
            return


        sobject = self.get_caller()
        pipeline_code = sobject.get_value("pipeline_code", no_exception=True)

        if not pipeline_code:
            return

        from pyasm.biz import Pipeline, Task
        from pyasm.search import SearchType

        try:
            pipeline = Pipeline.get_by_code(pipeline_code)
        except:
            # if pipeline does not exist
            pipeline = None

        if not pipeline:
            return

        if pipeline.get_value("autocreate_tasks", no_exception=True) not in ['true', True]:
            return

        #import time
        #start = time.time()
        Task.add_initial_tasks(sobject, pipeline_code=pipeline_code, skip_duplicate=True, mode='standard')

        #print("intial_tasks ...", search_key, time.time() - start)





class TaskCompleteTrigger(Trigger):
    '''This trigger is executed to state "officially" that the task is complete'''
    def execute(self):

        input = self.get_input()

        sobject = self.get_caller()

        if isinstance(sobject, Task):
            task = sobject
        else:
            process = input.get("process")
            raise Exception("Not supported yet")



        # get the task process
        process = task.get_value("process")
        status = task.get_value("status")


        pipeline_code = task.get_value("pipeline_code")
        if not pipeline_code:
            pipeline_code = 'task'

        task_pipeline = Pipeline.get_by_code(pipeline_code)
        if not task_pipeline:
            return
        # get the last process
        statuses = task_pipeline.get_process_names()
        if not statuses:
            return 


        completion_statuses = []
        for status in statuses:
            status_obj = task_pipeline.get_process(status)
            attrs = status_obj.get_attributes()
            completion = attrs.get("completion")
            if completion == "100":
                completion_statuses.append(status)

        if not completion_statuses:
            completion_statuses.append(statuses[-1])

        is_complete = False

        update_data = input.get('update_data')
        if update_data.get("status") in completion_statuses:
            is_complete = True


        if is_complete == True:
            #task.set_value("is_complete", True)
            if not task.get_value("actual_end_date"):
                task.set_now("actual_end_date")
                self.add_description('Internal Task Complete Trigger')
                task.commit(triggers=False)



