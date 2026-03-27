// Auto Generated - DO NOT EDIT
// Source: skill.xlsx
using System;
using System.Collections.Generic;
using UnityEngine;

namespace ST.Table
{
    /// <summary>
    /// Skill 表数据行（自动生成）
    /// </summary>
    public partial class TD_Skill
    {
        int m_Id = 0;
        string m_Name = string.Empty;
        float m_Damage = 0f;
        float m_Cooldown = 0f;
        bool m_IsAoe = false;
        string m_Desc = string.Empty;

        /// <summary>技能ID</summary>
        public int id => m_Id;
        /// <summary>技能名称</summary>
        public string name => m_Name;
        /// <summary>伤害值</summary>
        public float damage => m_Damage;
        /// <summary>冷却时间</summary>
        public float cooldown => m_Cooldown;
        /// <summary>是否AOE</summary>
        public bool isAoe => m_IsAoe;
        /// <summary>描述</summary>
        public string desc => m_Desc;

        /// <summary> 从二进制流读取 </summary>
        public void ParseFromBin(DataStreamReader reader)
        {
            m_Id = reader.ReadInt();
            m_Name = reader.ReadString();
            m_Damage = reader.ReadFloat();
            m_Cooldown = reader.ReadFloat();
            m_IsAoe = reader.ReadBool();
            m_Desc = reader.ReadString();
        }

        /// <summary> 从文本行读取 </summary>
        public void ParseFromTxt(string[] fields)
        {
            m_Id = int.Parse(fields[0]);
            m_Name = fields[1];
            m_Damage = float.Parse(fields[2]);
            m_Cooldown = float.Parse(fields[3]);
            m_IsAoe = fields[4] == "1" || fields[4].ToLower() == "true";
            m_Desc = fields[5];
        }
    }
}
