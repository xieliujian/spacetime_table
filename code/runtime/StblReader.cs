// Auto Generated - DO NOT EDIT
using System;
using System.IO;

namespace ST.Core.Table
{
    /// <summary>
    /// STBL 二进制表文件解析器。
    /// 校验文件头 magic，解析行数和数据偏移，提供定位到行数据的 DataStreamReader。
    /// </summary>
    public class StblReader
    {
        /// <summary> 数据行数（由文件头读取）</summary>
        public int rowCount { get; }

        /// <summary> 已定位到行数据起点的读取器 </summary>
        public DataStreamReader reader { get; }

        /// <summary>
        /// 解析 STBL 文件字节。
        /// 文件头布局（32 字节小端序）：magic[4] version[2] flags[2] fieldCount[2]
        /// rowCount[4@10] schemaOffset[4@14] dataOffset[4@18] reserved[10]
        /// </summary>
        public StblReader(byte[] data)
        {
            if (data == null || data.Length < 32)
                throw new InvalidDataException("STBL 数据不足 32 字节");

            if (data[0] != (byte)'S' || data[1] != (byte)'T' ||
                data[2] != (byte)'B' || data[3] != (byte)'L')
            {
                throw new InvalidDataException(
                    $"STBL magic 校验失败: 0x{data[0]:X2}{data[1]:X2}{data[2]:X2}{data[3]:X2}");
            }

            rowCount = (int)BitConverter.ToUInt32(data, 10);
            int dataOffset = (int)BitConverter.ToUInt32(data, 18);

            // 跳过行偏移表（rowCount × 4 字节）后即为行数据起点
            int rowDataStart = dataOffset + rowCount * 4;
            reader = new DataStreamReader(data, rowDataStart);
        }
    }
}
