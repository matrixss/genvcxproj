# 用于根据makefile建立一个VS2022的Linux工程。
# 说明： 建立的工程文件必须和makefile位于同一个目录下。

import codecs
import os
import sys
import hashlib
import uuid
import argparse
import json  # 导入json模块

from xml.dom.minidom import Document

support_configurations = ['Debug', 'Release']
support_platforms = ['x64']  # ['ARM', 'x86', 'x64']

# 文件分组信息
group_file_types_map = {
    'Source Files': {
        'extensions': ['.c', '.cpp', '.def', '.cxx', '.cc', '.c++', '.cp'],
        'group': 'sources_item_group',
        'element': 'ClCompile'
    },
    'Header Files': {
        'extensions': ['.h', '.hpp', '.hxx', '.hm', '.inl', '.inc', '.xsd'],
        'group': 'headers_item_group',
        'element': 'ClInclude'
    },
    # Makefile也放在该分组中.
    'Resource Files': {
        'extensions': ['.rc', '.ico', '.bmp', '.rc2', '.mk'],
        'group': 'resource_item_group',
        'element': 'None'
    }
}

# 其它文件，无法通过扩展名分组，直接指定文件名， 放在Resource Files目录中。
# 当前主要为Makefile文件。
filter_other_list = ["Makefile"]


def filter_dir(dir_name, proj_dir):
    """
    过滤目录函数，根据给定的目录参数判断是否需要过滤。
    返回值： True：表示过滤掉。
    """
    filter_dir_list = ['obj', 'bin', 'debug', 'release']
    # 替换为相对路径。
    work_dir_name = os.path.relpath(dir_name, proj_dir)
    for part in work_dir_name.split(os.path.sep):
        if part.startswith('.') and len(part) > 1:
            return True
        if part.lower() in filter_dir_list:
            return True
    return False


def filter_auto_gen_files(file_name):
    """
    过滤掉自动生产的特殊文件，例如.mod.c结尾的文件。
    返回值： True：表示过滤掉。
    """
    if file_name.endswith('.mod.c'):
        return True
    return False


# 通过字符串生成固定的GUID。
def generate_guid(input_str):
    # 将输入字符串转换为字节数组
    input_bytes = input_str.encode('utf-8')

    # 使用SHA1算法计算哈希值
    sha1 = hashlib.sha1()
    sha1.update(input_bytes)
    hash_value = sha1.hexdigest()

    guid = '{{{:0>8}-{:0>4}-{:0>4}-{:0>4}-{:0>12}}}'.format(hash_value[:8], hash_value[8:12], hash_value[12:16],
                                                            hash_value[16:20], hash_value[20:32])
    return guid


# 项目属性，主要为远程文件夹等参数。
def print_project_property_group(file):
    global support_configurations, support_platforms
    global parse_args

    remote_relative_dir = parse_args.relative_dir.replace("\\", "/")
    for platform in support_platforms:
        for configuration in support_configurations:
            file.write(
                f"  <PropertyGroup Condition=\"'$(Configuration)|$(Platform)'=='{configuration}|{platform}'\" Label=\"Configuration\">\n")
            if "debug" in configuration.lower():
                use_debug_libraries = "true"
            else:
                use_debug_libraries = "false"

            file.write(f"    <UseDebugLibraries>{use_debug_libraries}</UseDebugLibraries>\n")
            file.write(f"    <ConfigurationType>Makefile</ConfigurationType>\n")
            file.write(f"    <RemoteProjectRelDir>{remote_relative_dir}</RemoteProjectRelDir>\n")
            file.write(f"    <RemoteRootDir>{parse_args.remote_root_dir}</RemoteRootDir>\n")
            file.write(f"  </PropertyGroup>\n")


# build工具配置，主要为远程使用
def print_project_build_tools(file):
    global support_configurations, support_platforms
    global parse_args

    # 读取配置文件
    config_file_name = parse_args.config_file
    if os.path.isabs(config_file_name):
        config_path = config_file_name
    else:
        config_path = os.path.join(os.path.dirname(__file__), config_file_name)
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)

    for platform in support_platforms:
        for configuration in support_configurations:
            file.write(
                f"  <PropertyGroup Condition=\"'$(Configuration)|$(Platform)'=='{configuration}|{platform}'\">\n")

            if parse_args.copy_local_files_to_remote:
                file.write(f"    <LocalRemoteCopySources>true</LocalRemoteCopySources>\n")
            else:
                file.write(f"    <LocalRemoteCopySources>false</LocalRemoteCopySources>\n")

            if "debug" in configuration.lower():
                build_config = config["BuildDebugConfiguration"]
            else:
                build_config = config["BuildReleaseConfiguration"]

            # 处理特殊字符。
            def escape_special_chars(str_param):
                return str_param.replace("&&", "&amp;&amp;")

            # 使用配置文件中的命令，并处理特殊字符
            build_command = escape_special_chars(build_config["RemoteBuildCommandLine"])
            rebuild_command = escape_special_chars(build_config["RemoteReBuildCommandLine"])
            clean_command = escape_special_chars(build_config["RemoteCleanCommandLine"])

            file.write(f"    <RemoteBuildCommandLine>{build_command}</RemoteBuildCommandLine>\n")
            file.write(f"    <RemoteReBuildCommandLine>{rebuild_command}</RemoteReBuildCommandLine>\n")
            file.write(f"    <RemoteCleanCommandLine>{clean_command}</RemoteCleanCommandLine>\n")
            file.write(f"    <RemoteDeployDir>$(RemoteRootDir)/$(RemoteProjectRelDir)</RemoteDeployDir>\n")
            if len(parse_args.include_search_path) > 0:
                file.write(f"    <NMakeIncludeSearchPath>{parse_args.include_search_path}</NMakeIncludeSearchPath>\n")
            if len(parse_args.remote_build_outputs) > 0:
                file.write(f"    <RemoteBuildOutputs>{parse_args.remote_build_outputs}</RemoteBuildOutputs>\n")
            if len(parse_args.out_dir) > 0:
                file.write(f"    <OutDir>{parse_args.out_dir}</OutDir>\n")

            file.write(f"  </PropertyGroup>\n")


def printheader(file, proj_guid):
    """
    向给定的文件对象写入XML头部信息。为VS2022工程文件的头。
    """
    global support_configurations, support_platforms
    file.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
    file.write(
        "<Project DefaultTargets=\"Build\" ToolsVersion=\"14.0\" xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\">\n")
    file.write("  <ItemGroup Label=\"ProjectConfigurations\">\n")

    for platform in support_platforms:
        for configuration in support_configurations:
            file.write(f"    <ProjectConfiguration Include=\"{configuration}|{platform}\">\n")
            file.write(f"      <Configuration>{configuration}</Configuration>\n")
            file.write(f"      <Platform>{platform}</Platform>\n")
            file.write(f"    </ProjectConfiguration>\n")

    file.write("  </ItemGroup>\n")

    file.write("  <PropertyGroup Label=\"Globals\">\n")
    file.write("    <VCProjectVersion>17.0</VCProjectVersion>\n")
    file.write("    <ProjectGuid>{}</ProjectGuid>\n".format(proj_guid))
    file.write("    <Keyword>Linux</Keyword>\n")
    file.write("    <RootNamespace>makefile</RootNamespace>\n")
    file.write("    <MinimumVisualStudioVersion>14.0</MinimumVisualStudioVersion>\n")
    file.write("    <ApplicationType>Linux</ApplicationType>\n")
    file.write("    <ApplicationTypeRevision>1.0</ApplicationTypeRevision>\n")
    file.write("    <TargetLinuxPlatform>Generic</TargetLinuxPlatform>\n")
    file.write("    <LinuxProjectType>{FC1A4D80-50E9-41DA-9192-61C0DBAA00D2}</LinuxProjectType>\n")
    file.write("  </PropertyGroup>\n")
    file.write("  <Import Project=\"$(VCTargetsPath)\\Microsoft.Cpp.Default.props\" />\n")

    print_project_property_group(file)

    file.write("  <Import Project=\"$(VCTargetsPath)\\Microsoft.Cpp.props\" />\n")
    file.write("  <ImportGroup Label=\"ExtensionSettings\" />\n")
    file.write("  <ImportGroup Label=\"Shared\" />\n")
    file.write("  <ImportGroup Label=\"PropertySheets\" />\n")
    file.write("  <PropertyGroup Label=\"UserMacros\" />\n")

    print_project_build_tools(file)


def printfooter(file):
    file.write("  <ItemDefinitionGroup />\n")
    file.write("  <Import Project=\"$(VCTargetsPath)\\Microsoft.Cpp.targets\" />\n")
    file.write("  <ImportGroup Label=\"ExtensionTargets\" />\n")
    file.write("</Project>\n")


def listothers(file, proj_dir):
    global filter_other_list
    global group_file_types_map
    # others包含了不以下面扩展名结尾的文件。
    resourse_filter_list = group_file_types_map['Resource Files']['extensions']
    file.write("  <ItemGroup>\n")
    for root, dirs, files in os.walk(proj_dir):
        if filter_dir(root, proj_dir):
            continue
        for name in files:
            if any(name.endswith(ext) for ext in resourse_filter_list) or name in filter_other_list:
                d = os.path.dirname(os.path.join(root, name)).replace("/", "\\")
                # 替换为相对路径。
                d = d.replace(proj_dir, ".")
                f = os.path.basename(name)
                file.write(f"    <None Include=\"{d}\\{f}\" />\n")
    file.write("  </ItemGroup>\n")


def listtxt(file, proj_dir):
    file.write("  <ItemGroup>\n")
    for root, dirs, files in os.walk(proj_dir):
        if filter_dir(root, proj_dir):
            continue
        for name in files:
            if name.endswith(".txt"):
                d = os.path.dirname(os.path.join(root, name)).replace("/", "\\")
                # 替换为相对路径。
                d = d.replace(proj_dir, ".")
                f = os.path.basename(name)
                file.write(f"    <Text Include=\"{d}\\{f}\" />\n")
    file.write("  </ItemGroup>\n")


def listcompile(file, proj_dir):
    global group_file_types_map
    file.write("  <ItemGroup>\n")
    for root, dirs, files in os.walk(proj_dir):
        for name in files:
            if filter_auto_gen_files(name):
                continue
            if any(name.endswith(ext) for ext in group_file_types_map['Source Files']['extensions']):
                d = os.path.dirname(os.path.join(root, name)).replace("/", "\\")
                # 替换为相对路径。
                d = d.replace(proj_dir, ".")
                f = os.path.basename(name)
                file.write(f"    <ClCompile Include=\"{d}\\{f}\" />\n")
    file.write("  </ItemGroup>\n")


def listinclude(file, proj_dir):
    file.write("  <ItemGroup>\n")
    for root, dirs, files in os.walk(proj_dir):
        for name in files:
            if filter_auto_gen_files(name):
                continue
            if any(name.endswith(ext) for ext in group_file_types_map['Header Files']['extensions']):
                d = os.path.dirname(os.path.join(root, name)).replace("/", "\\")
                # 替换为相对路径。
                d = d.replace(proj_dir, ".")
                f = os.path.basename(name)
                file.write(f"    <ClInclude Include=\"{d}\\{f}\" />\n")
    file.write("  </ItemGroup>\n")


def generate_vcxproj(input_dir, output_file):
    proj_guid = generate_guid(output_file)
    out_file_path = os.path.join(input_dir, output_file)
    with codecs.open(out_file_path, "w", encoding='utf-8-sig') as f:
        printheader(f, proj_guid)
        listothers(f, input_dir)
        # listtxt(f, input_dir)
        listcompile(f, input_dir)
        listinclude(f, input_dir)
        printfooter(f)

    print(f"{out_file_path} generate complete.")


###########################################
def create_filter_element(doc, parent_item, filter_name, unique_id, extensions=None):
    """
    创建一个Filter元素，并设置其Include属性和UniqueIdentifier子元素。
    
    :param doc: XML文档对象。
    :param filter_name: Filter元素的Include属性值。
    :param unique_id: UniqueIdentifier元素的文本内容。
    :return: 创建的Filter元素。
    """
    filter_element = doc.createElement('Filter')
    filter_element.setAttribute('Include', filter_name)
    unique_identifier = doc.createElement('UniqueIdentifier')
    unique_identifier.appendChild(doc.createTextNode(unique_id))
    filter_element.appendChild(unique_identifier)
    if extensions:
        ext = doc.createElement('Extensions')
        ext.appendChild(doc.createTextNode(extensions))
        filter_element.appendChild(ext)

    parent_item.appendChild(filter_element)


def create_file_element(doc, parent_item, element_name, file_name, filter_name):
    file_element = doc.createElement(element_name)
    file_element.setAttribute('Include', file_name)
    filter_element = doc.createElement('Filter')
    filter_element.appendChild(doc.createTextNode(filter_name))
    file_element.appendChild(filter_element)
    parent_item.appendChild(file_element)


#  处理文件的过滤部分。例如
# <ClInclude Include=".\cap.h">
#    <Filter>Header Files</Filter>
# </ClInclude>
def process_files_for_types(doc, dir_path, rel_path, processed_dirs, filter_group_dirs, subfolder_item_group,
                            item_groups, file_types_map):
    global filter_other_list
    for filter_name, details in file_types_map.items():
        if filter_name == "Resource Files":  # 将Makefile放在资源文件分组中。
            files = [f for f in os.listdir(dir_path) if
                     any(f.endswith(ext) for ext in details['extensions']) or f in filter_other_list]
        else:
            files = [f for f in os.listdir(dir_path) if any(f.endswith(ext) for ext in details['extensions'])]
        if files:
            if len(rel_path) > 0:
                # 子目录
                processed_dirs.add(rel_path)  # 标记为已处理
                # 处理每一级目录
                rel_path_parts = rel_path.split('\\')
                current_path = ''
                for part in rel_path_parts:
                    current_path = os.path.join(current_path, part)
                    filter_part_rel_path = f"{filter_name}\\{current_path}"
                    if filter_part_rel_path not in filter_group_dirs:
                        create_filter_element(doc, subfolder_item_group, filter_part_rel_path,
                                              generate_guid(filter_part_rel_path))
                        filter_group_dirs.add(filter_part_rel_path)

                filter_rel_path = f"{filter_name}\\{rel_path}"

            else:
                # 工作目录。
                filter_rel_path = f"{filter_name}"

            for file in files:
                if filter_auto_gen_files(file):
                    continue
                if len(rel_path) > 0:
                    # 子目录
                    file_rel_path = f".\\{rel_path}\\{file}"
                else:
                    # 工作目录。
                    file_rel_path = f".\\{file}"
                create_file_element(doc, item_groups[details['group']], details['element'], file_rel_path,
                                    filter_rel_path)

            if len(rel_path) > 0:  # 子文件夹，在第一个itemgroup中添加一个类型。
                create_filter_element(doc, subfolder_item_group, filter_rel_path, generate_guid(filter_rel_path))
                filter_group_dirs.add(filter_rel_path)


# 生成过滤器
def generate_vcxproj_filters(input_dir, output_file):
    global group_file_types_map
    doc = Document()
    project = doc.createElement('Project')
    project.setAttribute('ToolsVersion', "4.0")
    project.setAttribute('xmlns', "http://schemas.microsoft.com/developer/msbuild/2003")
    doc.appendChild(project)

    subfolder_item_group = doc.createElement('ItemGroup')
    headers_item_group = doc.createElement('ItemGroup')
    sources_item_group = doc.createElement('ItemGroup')
    resource_item_group = doc.createElement('ItemGroup')
    project.appendChild(subfolder_item_group)
    project.appendChild(headers_item_group)
    project.appendChild(sources_item_group)
    project.appendChild(resource_item_group)

    processed_dirs = set()  # 用于记录已处理的目录
    filter_group_dirs = set()  # 用于记录已处理的分组信息

    # 添加3个默认的分组。为根目录下的文件
    create_filter_element(doc, subfolder_item_group, "Source Files", "{4FC737F1-C7A5-4376-A066-2A32D752A2FF}",
                          "cpp;c;cc;cxx;def;odl;idl;hpj;bat;asm;asmx")
    create_filter_element(doc, subfolder_item_group, "Header Files", "{93995380-89BD-4b04-88EB-625FBE52EBFB}",
                          "h;hpp;hxx;hm;inl;inc;xsd")
    create_filter_element(doc, subfolder_item_group, "Resource Files", "{67DA6AB6-F800-4c08-8B7A-83BB121AAD01}",
                          "rc;ico;cur;bmp;dlg;rc2;rct;bin;rgs;gif;jpg;jpeg;jpe;resx;tiff;tif;png;wav;mfcribbon-ms")

    item_groups = {
        'sources_item_group': sources_item_group,
        'headers_item_group': headers_item_group,
        'resource_item_group': resource_item_group
    }

    # 遍历当前目录下的所有子目录
    for root, dirs, files in os.walk(input_dir, topdown=True):
        if root == input_dir:
            process_files_for_types(doc, root, "", processed_dirs, filter_group_dirs, subfolder_item_group, item_groups,
                                    group_file_types_map)

        for name in dirs:
            dir_path = os.path.join(root, name)
            if filter_dir(dir_path, input_dir):
                continue
            rel_path = os.path.relpath(dir_path, input_dir)  # 计算相对路径

            if rel_path in processed_dirs:  # 如果该目录已处理，跳过
                continue

            process_files_for_types(doc, dir_path, rel_path, processed_dirs, filter_group_dirs, subfolder_item_group,
                                    item_groups, group_file_types_map)

    # 写入xml文件。
    out_file_path = os.path.join(input_dir, output_file)
    with codecs.open(out_file_path, "wb", encoding='utf-8-sig') as f:
        xml_str = doc.toprettyxml(indent="  ", encoding="utf-8")
        # 将XML字符串的换行符从Unix格式转换为Windows格式
        xml_str_windows_format = xml_str.replace(b'\n', b'\r\n')
        f.write(xml_str_windows_format.decode('utf-8'))

    print(f"{out_file_path} generate complete.")


def check_makefile(directory):
    makefile_path = os.path.join(directory, 'Makefile')
    return os.path.isfile(makefile_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # 是否复制本地文件到远程文件夹。
    # 如果使用了映射Windows共享文件夹的方式，则不需要复制。否则，需要复制。默认不复制。
    parser.add_argument("-c", "--copy_local_files_to_remote", action='store_true', help="copy local files to remote")
    parser.add_argument("-f", "--config_file",
                        help="specify the name of an optional configuration file, if not specified, use config.json",
                        default="config.json")
    parser.add_argument("-i", "--include_search_path",
                        help="specify the path to search for include files not in the project directory", default="")
    # 项目在远程的输出文件，可以为空。
    parser.add_argument("-b", "--remote_build_outputs",
                        help="specify the path to the output file", default="")
    # 设置本地的生成文件路径。如果设置了-b参数，可以将远程生成的文复制到在该目录下。
    # 参考设置：$(SolutionDir)bin\$(Platform)\$(Configuration)\
    parser.add_argument("-o", "--out_dir",
                        help="specify the local output path", default="")
    parser.add_argument("local_root_dir", help="local root dir")
    parser.add_argument("relative_dir", help="Makefile relative dir to local_root_dir")
    # 远程主机的目录，和local_root_dir对应。
    parser.add_argument("remote_root_dir", help="root dir in remote machine")
    # 生成的vcxproj文件名。文件保存在Makefile所在目录（local_root_dir + relative_dir）
    parser.add_argument("output_vcxproj_file", help="output vcxproj file name")

    parse_args = parser.parse_args()

    input_dir = os.path.join(parse_args.local_root_dir, parse_args.relative_dir)
    output_vcxproj_file = parse_args.output_vcxproj_file
    output_vcxproj_filters_file = output_vcxproj_file + ".filters"

    # print(f"include_search_path : {parse_args.include_search_path}")
    # print(f"remote_build_outputs : {parse_args.remote_build_outputs}")
    # print(f"out_dir : {parse_args.out_dir}")

    # 确认目录下Makefile是否存在。
    if not check_makefile(input_dir):
        print("Makefile is not exist.")
        exit

    print(f"=======================")
    generate_vcxproj(input_dir, output_vcxproj_file)
    generate_vcxproj_filters(input_dir, output_vcxproj_filters_file)
