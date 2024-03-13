# 功能说明

基于Makefile，建立VC2022的Linux开发工程；

参考：[Visual C++ for Linux Development extension](http://aka.ms/vslinux). 

# 使用场景示例

参考下面的目录，脚本对于每一个MakeFile需要执行一次。

```
local_root_dir:
    - relative_dir01
    	- Makefile
    	- test1.c
    	- test2.c
    	- test1.h
    	- test2.h
    - relative_dir02
        - Makefile
    	- test1.c
    	- test2.c
    	- test1.h
    	- test2.h
```

注意：relative_dir01下面的Makefile不要应用relative_dir02中的源文件，当前脚本不会分析Makefile，因此，不会将relative_dir02目录下的文件添加到relative_dir01的工程中。

# 使用说明

该文件为一个python脚本，在Windows下使用。

包含2个文件：

* genvcxproj.py： 用于VC生成工程文件；

* config.json： 对编译命令进行配置, 可以根据实际需要修改，对应VC中的参考如下（对应Debug和Release两种配置）：

  ```
  {
  	"BuildDebugConfiguration": {
          "RemoteBuildCommandLine": "make CONFIG=DEBUG",
          "RemoteReBuildCommandLine": "make CONFIG=DEBUG clean && make CONFIG=DEBUG",
          "RemoteCleanCommandLine": "make CONFIG=DEBUG clean"
      },
      "BuildReleaseConfiguration": {
          "RemoteBuildCommandLine": "make",
          "RemoteReBuildCommandLine": "make clean && make",
          "RemoteCleanCommandLine": "make clean"
      }
  }
  ```

使用方式:

```
genvcxproj.py [-h] [-c COPY_LOCAL_FILES_TO_REMOTE] [-f CONFIG_FILE] [-i INCLUDE_SEARCH_PATH]
                     local_root_dir relative_dir remote_root_dir output_vcxproj_file
```

参数说明：

* -c： 是否将本地修改的文件复制到到远程，默认不复制（如果使用Linux共享文件夹的方式，则设置为不复制，如果为独立目录，则复制）；
* -f： 指定一个配置文件，可以对工程的编译命令进行配置，参考config.json文件，如果不指定，则默认使用config.json. 可以使用绝对路径，如果不是绝对路径，则路径是相对于genvcxproj.py所在目录的。
* -i： 如果有include文件位于其它目录，可以使用该选项包含, 多个目录使用(和编译无关，只和IntelliSense有关)；分割。 例如: `$(ProjectDir)\..\inc;$(ProjectDir)\..\..\common`
* -b: 设置编译后远程生成的文件路径，设置后，默认为Debug的目标文件。该文件也会复制到本地OutDir中。
* -o: 设置本地的生成文件路径。如果设置了-b参数，可以将远程生成的文复制到在该目录下。 参考设置："$(SolutionDir)bin\$(Platform)\$(Configuration)"
* local_root_dir：解决方案根目录，可以包含有多个工程，该文件夹用于指定工程集合的根
* relative_dir：本地工程对于local_root_dir的相对路径。
* remote_root_dir: 远程解决方案的根目录；
* output_vcxproj_file：生成的文件名子，不包含路径。该文件会保存在relative_dir目录下，和Makefile位于相同目录，以便于VC解析错误信息。

其它说明：

* 在生成vcxproj时，会同时生成`.vcxproj.filters`文件，该文件按照文件类型和文件夹对文件进行分类。
* 当前会生成2个配置（Debug/Release），一个平台(x64)，可以通过config.json配置不同的构建方式。
  * 如果需要其它平台，可以修改源码。

* 如果有其它文件夹或者文件类型需要过滤，可以修改源码中的filter_dir和filter_auto_gen_files函数。

# 示例

下面为一个参考批处理文件：

```
@echo off
set PRJ_ROOT_DIR=%~dp0
if "%PRJ_ROOT_DIR:~-1%"=="\" set PRJ_ROOT_DIR=%PRJ_ROOT_DIR:~0,-1%

set SCRIPT_FILE=E:\Script\genvcxproj.py
set REMOTE_ROOT_DIR=~/workspace/project_dir
:: 是否将文件复制到远程，如果为空，则不复制。如果复制，设置为-c
set COPY_TO_REMOTE=

python "%SCRIPT_FILE%" %COPY_TO_REMOTE% "%PRJ_ROOT_DIR%" relative_dir01 "%REMOTE_ROOT_DIR%" proj01.vcxproj
python "%SCRIPT_FILE%" %COPY_TO_REMOTE% -f config2.json "%PRJ_ROOT_DIR%" relative_dir02 "%REMOTE_ROOT_DIR%" proj02.vcxproj

PAUSE
```

生成工程文件之后，可以手工建立一个空的sln文件（或者从已有工程中复制一个sln文件，删除其中的工程即可），将生成的vcxproj文件，加入到sln文件中，根据需要做相关配置修改。

