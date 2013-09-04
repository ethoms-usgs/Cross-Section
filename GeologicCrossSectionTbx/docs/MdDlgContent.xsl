<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
                version="1.0">

<xsl:output method="html"/>

<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<!--                 Variable Definitions                   -->
<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->

<xsl:variable name="BackgroundColor">buttonface</xsl:variable>
<xsl:variable name="BackgroundImage">url(<xsl:value-of select="MdElementDialogInfo/CommonPath"/>/usgs.gif)</xsl:variable>
<xsl:variable name="BackgroundPosition">bottom right</xsl:variable>
<xsl:variable name="BackgroundRepeat">no-repeat</xsl:variable>

<xsl:variable name="ButtonHeight">20px</xsl:variable>
<xsl:variable name="ButtonFont">Arial</xsl:variable>
<xsl:variable name="ButtonFontSize">8pt</xsl:variable>
<xsl:variable name="ButtonColor">buttontext</xsl:variable>
<xsl:variable name="ButtonBackgroundColor">ButtonFace</xsl:variable>
<xsl:variable name="ButtonBorderColorTop">threedhighlight</xsl:variable>
<xsl:variable name="ButtonBorderColorLeft">threedhighlight</xsl:variable>
<xsl:variable name="ButtonBorderColorBottom">threedshadow</xsl:variable>
<xsl:variable name="ButtonBorderColorRight">threedshadow</xsl:variable>
<xsl:variable name="ButtonBorderStyleTop">ridge</xsl:variable>
<xsl:variable name="ButtonBorderStyleLeft">ridge</xsl:variable>
<xsl:variable name="ButtonBorderStyleBottom">groove</xsl:variable>
<xsl:variable name="ButtonBorderStyleRight">groove</xsl:variable>
<xsl:variable name="ButtonBorderWidth">2px</xsl:variable>

<xsl:variable name="CaptionFont">verdana,arial</xsl:variable>
<xsl:variable name="CaptionSize">8pt</xsl:variable>
<xsl:variable name="CaptionColor">Black</xsl:variable>
<xsl:variable name="CaptionWeight">Normal</xsl:variable>
<xsl:variable name="CaptionStyle">Normal</xsl:variable>

<xsl:variable name="GroupHeadingFont">verdana,arial</xsl:variable>
<xsl:variable name="GroupHeadingSize">8pt</xsl:variable>
<xsl:variable name="GroupHeadingColor">Black</xsl:variable>
<xsl:variable name="GroupHeadingWeight">Bold</xsl:variable>
<xsl:variable name="GroupHeadingStyle">Normal</xsl:variable>

<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<!--              MdElementDialogInfo Template              -->
<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<xsl:template match="MdElementDialogInfo">
<HTML> 
  <xsl:attribute name="DIR">
    <xsl:value-of select="Direction" />
  </xsl:attribute>
<HEAD>
  <TITLE>Content</TITLE>
  <STYLE TYPE="text/css">
  BODY {
    background-color :    <xsl:value-of select="$BackgroundColor" />;
    background-image :    <xsl:value-of select="$BackgroundImage" />;
    background-position : <xsl:value-of select="$BackgroundPosition" />;
    background-repeat :   <xsl:value-of select="$BackgroundRepeat" />;
  }
  .button {   height:               <xsl:value-of select="$ButtonHeight" />; 
              font-family:          <xsl:value-of select="$ButtonFont" />; 
              font-size:            <xsl:value-of select="$ButtonFontSize" />; 
              color:                <xsl:value-of select="$ButtonColor" />; 
              background-color:     <xsl:value-of select="$ButtonBackgroundColor" />; 
              border-top-color:     <xsl:value-of select="$ButtonBorderColorTop" />; 
              border-left-color:    <xsl:value-of select="$ButtonBorderColorLeft" />; 
              border-bottom-color:  <xsl:value-of select="$ButtonBorderColorBottom" />; 
              border-right-color:   <xsl:value-of select="$ButtonBorderColorRight" />; 
              border-top-style:     <xsl:value-of select="$ButtonBorderStyleTop" />; 
              border-left-style:    <xsl:value-of select="$ButtonBorderStyleLeft" />; 
              border-bottom-style:  <xsl:value-of select="$ButtonBorderStyleBottom" />; 
              border-right-style:   <xsl:value-of select="$ButtonBorderStyleRight" />; 
              border-width:         <xsl:value-of select="$ButtonBorderWidth" />; } 
  .caption {  font-family:          <xsl:value-of select="$CaptionFont"/>; 
              font-size:            <xsl:value-of select="$CaptionSize"/>; 
              color:                <xsl:value-of select="$CaptionColor"/>; 
              font-weight:          <xsl:value-of select="$CaptionWeight"/>; 
              font-style:           <xsl:value-of select="$CaptionStyle"/>;}
  .groupheading {  font-family:          <xsl:value-of select="$GroupHeadingFont"/>; 
                   font-size:            <xsl:value-of select="$GroupHeadingSize"/>; 
                   color:                <xsl:value-of select="$GroupHeadingColor"/>; 
                   font-weight:          <xsl:value-of select="$GroupHeadingWeight"/>; 
                   font-style:           <xsl:value-of select="$GroupHeadingStyle"/>;}
  .small { font-family: verdana,arial; font-size: 7pt; }
</STYLE><xsl:text>&#10;</xsl:text>

<xsl:comment> ================ Scripts ================ </xsl:comment>
<xsl:text>&#10;</xsl:text>

<SCRIPT language="JavaScript"><xsl:text>&#10;</xsl:text>
<xsl:comment>
<![CDATA[
function InitForm()
{ ]]>
  // Register each control...
  //
<xsl:for-each select="Properties/PropertyGroup">
<xsl:for-each select="Property">  
   window.external.RegisterControl(<xsl:value-of select="CtrlName"/>, &quot;<xsl:value-of select="PropertyName"/>&quot;, &quot;<xsl:value-of select="Dependency"/>&quot;);
   <xsl:choose> 
     <xsl:when test="CtrlPlacement = 'below'">
       window.external.RegisterControl(<xsl:value-of select="CtrlLabel"/>, &quot;<xsl:value-of select="PropertyName"/>&quot;, &quot;<xsl:value-of select="Dependency"/>&quot;);
     </xsl:when>
  </xsl:choose>
</xsl:for-each>
</xsl:for-each><![CDATA[
  // Update the property image
  //
  var msg;]]>
<xsl:for-each select="Properties/PropertyGroup">
<xsl:for-each select="Property">  
  msg = window.external.GetMessage(&quot;<xsl:value-of select="PropertyName"/>&quot;);
  UpdatePropertyIcon(&quot;<xsl:value-of select="PropertyName"/>Img&quot;, msg);
</xsl:for-each>
</xsl:for-each><![CDATA[
  Window_onresize();
}

function Window_onresize()
{ ]]>
  // Resize each control...
  //
  if ((window.document.body.clientWidth - 90) > 0)
  {
    <xsl:for-each select="Properties/PropertyGroup">
    <xsl:for-each select="Property">  <xsl:value-of select="CtrlName"/>.width = window.document.body.clientWidth - 90;
    </xsl:for-each>
    </xsl:for-each><![CDATA[
  }
}

function UpdatePropertyIcon(img, msg)
{
  var imgSource;
  var description = "";
  if (msg && msg.IsError())
  {
    description = msg.Description;
    if (msg.Type == 101)]]>
      imgSource = &quot;<xsl:value-of select='CommonPath'/>/msgarrow.gif&quot;;
    else
      imgSource = &quot;<xsl:value-of select='CommonPath'/>/msgerror.gif&quot;;<![CDATA[
  }
  else if (msg && msg.IsWarning())
  {
    description = msg.Description;]]>
    imgSource = &quot;<xsl:value-of select='CommonPath'/>/msgwarning.gif&quot;;<![CDATA[
  }
  else
  {
    if (msg)
      description = msg.Description;]]>
    imgSource = &quot;<xsl:value-of select='CommonPath'/>/msgempty.gif&quot;;<![CDATA[
  }

  document.getElementById(img).alt = description;
  document.getElementById(img).src = imgSource;

}

function UpdatePropertyIcons()
{
  // Update the warning/error icon for each property]]>
  var msg;
<xsl:for-each select="Properties/PropertyGroup">
  <xsl:for-each select="Property">  
  msg = window.external.GetMessage(&quot;<xsl:value-of select="PropertyName"/>&quot;);
  UpdatePropertyIcon(&quot;<xsl:value-of select="PropertyName"/>Img&quot;, msg);
  </xsl:for-each>
</xsl:for-each><![CDATA[ 
}

//
// HELP TOPIC NOTES: 
//
// Originally we had onClick() handlers for the BODY, DIV, and (property) SPAN 
// elements that would display the corresponding help topic. When clicking on 
// the SPAN element ShowHelpTopic() was being called correctly, however, the 
// onClick() handler for the BODY/DIV element was immediately called, causing 
// the currently displayed help topic to change to the 'Intro' topic. 
//
// To correct this, I've changed the onClick() handler for the SPAN elements
// to set a global 'current-topic' variable (g_currentHelpTopic), and rely on 
// the onClick() handlers for the BODY/DIV elements to call ShowCurrentHelpTopic() 
// to actually display the current topic. ShowCurrentHelpTopic() clears the 
// g_currentHelpTopic variable before returning, and displays the 'Intro' 
// topic.
//

g_currentHelpTopic = '';

function ShowHelpTopic(topic)
{
  SetCurrentHelpTopic(topic);
  ShowCurrentHelpTopic();
}

function SetCurrentHelpTopic(topic)
{
  g_currentHelpTopic = topic;
}

function ShowCurrentHelpTopic()
{
  window.external.ShowHelpTopic(g_currentHelpTopic);
  g_currentHelpTopic = '';
}

function clicker(a,b) 
{
  if (a.style.display =='') 
  {
    a.style.display = 'none';
]]>    b.src='<xsl:value-of select="CommonPath"/>/triangle.gif'; <![CDATA[
  }
  else 
  {
    a.style.display='';
]]>    b.src='<xsl:value-of select="CommonPath"/>/triangle2.gif'; <![CDATA[
    window.external.UpdateCtrlTabOrder();
  }
}

]]>
</xsl:comment><xsl:text>&#10;</xsl:text>
</SCRIPT><xsl:text>&#10;</xsl:text>

<xsl:text>&#10;</xsl:text>
<SCRIPT language="JavaScript" FOR='window' EVENT='onunload'><xsl:text>&#10;</xsl:text>
<xsl:comment>
<![CDATA[
  window.external.UnRegisterControls();
]]>
</xsl:comment><xsl:text>&#10;</xsl:text>
</SCRIPT><xsl:text>&#10;</xsl:text>
<xsl:text>&#10;</xsl:text>

</HEAD><xsl:text>&#10;</xsl:text>

<BODY onload="InitForm()" TEXT="windowtext" onresize="Window_onresize()" onclick="ShowCurrentHelpTopic();"><xsl:text>&#10;</xsl:text>
<SCRIPT language="Javascript" src="{CommonPath}/disableclick.js"></SCRIPT><xsl:text>&#10;</xsl:text>

<DIV STYLE="margin:0em 0.5em 0.5em 1em;"><xsl:text>&#10;</xsl:text>
<xsl:apply-templates select="Intro" />

<xsl:for-each select="Properties">
    <xsl:apply-templates/>
</xsl:for-each>
</DIV>

</BODY>
</HTML>
</xsl:template>


<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<!--                 Property Group Template                -->
<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<xsl:template match="PropertyGroup">
  <xsl:choose> 
    <xsl:when test="PropertyGroupLabelVisibility = 'show'">
      <TR valign="top">
        <TD colspan="2">
          <DIV ID="GEN" STYLE="cursor: hand;">
            <TABLE onclick="clicker({PropertyGroupName},{PropertyGroupName}Image);" STYLE="cursor:hand;" border="1" bordercolor="menu" cellspacing="0" cellpadding="0" width="90%">
              <TR valign="top" bgcolor="menu">
                <TD colspan="2">
                  <TABLE border="0" cellpadding="0" cellspacing="0" width="100%" >
                    <TR bgcolor="menu">
                      <xsl:choose>
                        <xsl:when test="../../Direction = 'ltr' ">
                          <TH align="left">
                          <IMG ID="{PropertyGroupName}Image" SRC="{../../CommonPath}/triangle.gif" ALT="*" ALIGN="LEFT" BORDER="0" WIDTH="11" HEIGHT="11"/>
                          <SPAN class="groupheading" STYLE="color:menutext;"><xsl:value-of select="PropertyGroupLabel"/></SPAN>
                          </TH>
                        </xsl:when>
                        
                        <xsl:otherwise>
                          <TH align="right">
                          <IMG ID="{PropertyGroupName}Image" SRC="{../../CommonPath}/triangle.gif" ALT="*" ALIGN="RIGHT" BORDER="0" WIDTH="11" HEIGHT="11"/>
                          <SPAN class="groupheading" STYLE="color:menutext;"><xsl:value-of select="PropertyGroupLabel"/></SPAN>
                          </TH>
                        </xsl:otherwise>
                      </xsl:choose>
                      
                    </TR>
                  </TABLE>
                </TD>
              </TR>

              <TR valign="top">
                <TD colspan="2">
                  <DIV ID="{PropertyGroupName}" STYLE="display:'none';" onclick="window.event.cancelBubble = true;">
                    <xsl:for-each select="Property"> 
                      <xsl:apply-templates select="." />
                    </xsl:for-each> 
                  </DIV>
                </TD>
              </TR>

            </TABLE>
          </DIV>
        </TD>
      </TR>
    </xsl:when>

    <xsl:otherwise>
      <TR valign="top">
        <TD colspan="2">
        <TABLE border="0" cellspacing="0" cellpadding="0" width="90%">
        <xsl:for-each select="Property"> 
          <xsl:apply-templates select="." />
        </xsl:for-each> 
        </TABLE>
        </TD>
      </TR>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<!--                 Property Template                      -->
<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<xsl:template match="Property">
  <TABLE BORDER="0" CELLSPACING="2" CELLPADDING="4" WIDTH="90%">
    <TR valign="top">
      <TD WIDTH='17'>
        <IMG ID='{PropertyName}Img' src="{../../../CommonPath}/msgempty.gif" />
      </TD>

      <xsl:choose> 
        <xsl:when test="CtrlPlacement = 'side'">
          <TD>
          <TABLE>
          <TR>
            <TD>
              <OBJECT classid="CLSID:{CtrlCLSID}" id="{CtrlName}" onfocus="ShowHelpTopic('{PropertyName}Topic');" /> 
            </TD>
          </TR>
          </TABLE>
          </TD>
        </xsl:when>

        <xsl:otherwise>
          <TD>
            <OBJECT classid="CLSID:9FA602C6-85AF-40E2-A64A-E938C70C67B9" id="{CtrlLabel}" onfocus="ShowHelpTopic('{PropertyName}Topic');" /> 
            <OBJECT classid="CLSID:{CtrlCLSID}" id="{CtrlName}" onfocus="ShowHelpTopic('{PropertyName}Topic');" /> 
          </TD>
        </xsl:otherwise>
      </xsl:choose>

    </TR>
  </TABLE>
</xsl:template>

<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<!--                   Intro Template                       -->
<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<xsl:template match="Intro">
  <div align="center">
  <b>
  <br/>
  <xsl:value-of select="." />
  </b>
  </div>
</xsl:template>

<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<!--                   Root Template                        -->
<!--                                                        -->
<!-- Matches the whole document, where processing begins    -->
<!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->
<xsl:template match="/">
  <xsl:apply-templates />
</xsl:template>

</xsl:stylesheet>


