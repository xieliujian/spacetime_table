// Auto Generated - DO NOT EDIT
using System.Text;
using UnityEngine;

namespace ST.Core.Table
{
    /// <summary>
    /// 二进制字节流读取器，支持 varint / zigzag 编码及所有配表字段类型。
    /// </summary>
    public class DataStreamReader
    {
        byte[] m_Buffer;
        int m_Pos;

        public DataStreamReader(byte[] data, int startPos = 0)
        {
            if (data == null) throw new System.ArgumentNullException(nameof(data));
            m_Buffer = data;
            m_Pos = startPos;
        }

        /// <summary> 读取 zigzag varint → int32 </summary>
        public int ReadInt()
        {
            uint n = (uint)ReadVarint();
            return ZigzagDecode32(n);
        }

        /// <summary> 读取 zigzag varint → int64 </summary>
        public long ReadInt64()
        {
            ulong n = ReadVarint();
            return ZigzagDecode64(n);
        }

        /// <summary> 读取 4 字节小端序 float32 </summary>
        public float ReadFloat()
        {
            float v = System.BitConverter.ToSingle(m_Buffer, m_Pos);
            m_Pos += 4;
            return v;
        }

        /// <summary> 读取 1 字节，非 0 为 true </summary>
        public bool ReadBool()
        {
            return ReadRawByte() != 0;
        }

        /// <summary> 读取 2 字节 LE 长度前缀 + UTF-8 字符串 </summary>
        public string ReadString()
        {
            ushort len = ReadUInt16LE();
            if (len == 0) return string.Empty;
            string s = Encoding.UTF8.GetString(m_Buffer, m_Pos, len);
            m_Pos += len;
            return s;
        }

        /// <summary> 读取 1 字节 </summary>
        public byte ReadByte()
        {
            return ReadRawByte();
        }

        /// <summary> 读取 2 × float32 → Vector2 </summary>
        public Vector2 ReadVector2()
        {
            float x = ReadFloat();
            float y = ReadFloat();
            return new Vector2(x, y);
        }

        /// <summary> 读取 3 × float32 → Vector3 </summary>
        public Vector3 ReadVector3()
        {
            float x = ReadFloat();
            float y = ReadFloat();
            float z = ReadFloat();
            return new Vector3(x, y, z);
        }

        // ---- 私有辅助 ----

        byte ReadRawByte()
        {
            return m_Buffer[m_Pos++];
        }

        ushort ReadUInt16LE()
        {
            ushort v = (ushort)(m_Buffer[m_Pos] | (m_Buffer[m_Pos + 1] << 8));
            m_Pos += 2;
            return v;
        }

        uint ReadUInt32LE()
        {
            uint v = (uint)(m_Buffer[m_Pos]
                         | (m_Buffer[m_Pos + 1] << 8)
                         | (m_Buffer[m_Pos + 2] << 16)
                         | (m_Buffer[m_Pos + 3] << 24));
            m_Pos += 4;
            return v;
        }

        ulong ReadVarint()
        {
            ulong result = 0;
            int shift = 0;
            byte b;
            do
            {
                b = ReadRawByte();
                result |= (ulong)(b & 0x7F) << shift;
                shift += 7;
            } while ((b & 0x80) != 0);
            return result;
        }

        static int ZigzagDecode32(uint n)
        {
            return (int)((n >> 1) ^ (uint)(-(int)(n & 1)));
        }

        static long ZigzagDecode64(ulong n)
        {
            return (long)((n >> 1) ^ (ulong)(-(long)(n & 1)));
        }
    }
}
