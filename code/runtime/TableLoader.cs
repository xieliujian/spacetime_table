// Auto Generated - DO NOT EDIT
using System.IO;

namespace ST.Core.Table
{
    /// <summary>
    /// 表格文件加载工具，提供文件字节和文本的读取接口。
    /// </summary>
    public static class TableLoader
    {
        /// <summary>
        /// 读取文件全部字节。文件不存在时抛出含路径信息的异常。
        /// </summary>
        public static byte[] LoadBytes(string path)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException($"表格文件不存在: {path}", path);
            return File.ReadAllBytes(path);
        }

        /// <summary>
        /// 读取 UTF-8（含 BOM）文本文件。文件不存在时抛出含路径信息的异常。
        /// </summary>
        public static string LoadText(string path)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException($"表格文件不存在: {path}", path);
            return File.ReadAllText(path);
        }
    }
}
