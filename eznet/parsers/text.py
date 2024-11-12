# import re
#
#
# def key_reduce(key):
#     if isinstance(key, (list, tuple)) and len(key) == 1:
#         key = key[0]
#     if isinstance(key, str) and key.count('.'):
#         key = key.split('.')
#     return key
#
#
# def s_set(array, key, value):
#     key = key_reduce(key)
#     if not isinstance(key, list):
#         array[key] = value
#     else:
#         if key[0] not in array:
#             array[key[0]] = dict()
#         s_set(array[key[0]], key[1:], value)
#
#
# class TextParser:
#     def __init__(self, template):
#         self.template = template
#
#     def __call__(self, input_file):
#
#         templates = [self.template]
#         output = [dict()]
#
#         for line in input_file.readlines():
#
#             matched = False
#             for level, template in enumerate(templates):
#                 for item in template:
#                     if 'regexp' not in item:
#                         continue
#                     result = re.match(item['regexp'], line)
#                     if result is not None:
#                         templates = templates[:level+1]
#                         output = output[:level+1]
#
#                         if 'key' in item:
#                             key = item['key'].format(**result.groupdict())
#                         else:
#                             key = None
#                         if 'value' in item:
#                             if isinstance(item['value'], str):
#                                 value = item['value'].format(**result.groupdict())
#                             elif isinstance(item['value'], list):
#                                 value = dict()
#                                 for it in item['value']:
#                                     if 'regexp' not in it and 'key' in it:
#                                         if 'value' in it:
#                                             v = it['value'].format(**result.groupdict())
#                                         else:
#                                             v = dict()
#                                         # FIXME: w/a for preventing 'None' in values
#                                         if 'None' not in v:
#                                             s_set(value, it['key'], v)
#                                 templates.append(item['value'])
#                                 output.append(value)
#                             else:
#                                 value = None
#                         else:
#                             value = dict()
#                         if key is not None and value is not None:
#                             s_set(output[level], key, value)
#
#                         matched = True
#                         break
#                 if matched:
#                     break
#
#         return output[0]
#
# import re
#
# def key_reduce(key):
#     if isinstance(key, (list, tuple)) and len(key) == 1:
#         key = key[0]
#     if isinstance(key, str) and key.count('.'):
#         key = key.split('.')
#     return key
#
# def s_set(array, key, value):
#     key = key_reduce(key)
#     if not isinstance(key, list):
#         array[key] = value
#     else:
#         if key[0] not in array:
#             array[key[0]] = dict()
#         s_set(array[key[0]], key[1:], value)
#
# class Parser:
#     def __init__(self, template):
#         self.template = template
#
#     def parse(self, input_file):
#
#         templates = [self.template]
#         output = [dict()]
#
#         line = input_file.readline()
#         while line:
#             # print(line, end='')
#             matched = False
#             line = input_file.readline()
#
#             for level in range(len(templates)):
#                 for item in templates[level]:
#                     if 'regexp' not in item:
#                         continue
#                     result = re.match(item['regexp'], line)
#                     if result is not None:
#                         templates = templates[:level + 1]
#                         output = output[:level + 1]
#
#                         if 'key' in item:
#                             key = item['key'].format(**result.groupdict())
#                         else:
#                             key = None
#                         if 'value' in item:
#                             if isinstance(item['value'], str):
#                                 value = item['value'].format(**result.groupdict())
#                             elif isinstance(item['value'], list):
#                                 value = dict()
#                                 for it in item['value']:
#                                     if 'regexp' not in it and 'key' in it:
#                                         if 'value' in it:
#                                             v = it['value'].format(**result.groupdict())
#                                         else:
#                                             v = dict()
#                                         # TODO w/a for preventing 'None' in values
#                                         if not 'None' in v:
#                                             s_set(value, it['key'], v)
#                                 templates.append(item['value'])
#                                 output.append(value)
#                             else:
#                                 value = None
#                         else:
#                             value = dict()
#                         if key is not None and value is not None:
#                             # print("key: {}, value: {}".format(key, value))
#                             s_set(output[level], key, value)
#
#                         matched = True
#                         break
#                 if matched:
#                     break
#
#         return output[0]
