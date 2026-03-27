// Auto Generated - DO NOT EDIT
// Source: item.xlsx
using System;
using System.Collections.Generic;
using UnityEngine;

namespace ST.Table
{
    /// <summary>
    /// Item 表数据行（自动生成）
    /// </summary>
    public partial class TD_Item
    {
        int m_Id = 0;
        string m_Name = string.Empty;
        int m_Price = 0;
        bool m_Stackable = false;

        /// <summary>物品ID</summary>
        public int id => m_Id;
        /// <summary>物品名称</summary>
        public string name => m_Name;
        /// <summary>售价</summary>
        public int price => m_Price;
        /// <summary>可堆叠</summary>
        public bool stackable => m_Stackable;

        /// <summary> 从二进制流读取 </summary>
        public void ParseFromBin(DataStreamReader reader)
        {
            m_Id = reader.ReadInt();
            m_Name = reader.ReadString();
            m_Price = reader.ReadInt();
            m_Stackable = reader.ReadBool();
        }

        /// <summary> 从文本行读取 </summary>
        public void ParseFromTxt(string[] fields)
        {
            m_Id = int.Parse(fields[0]);
            m_Name = fields[1];
            m_Price = int.Parse(fields[2]);
            m_Stackable = fields[3] == "1" || fields[3].ToLower() == "true";
        }
    }
}
